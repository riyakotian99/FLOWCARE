from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any

from pymongo import MongoClient, ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError


# ------------------------------
# Utility helpers for (de)serializing dates
# ------------------------------

def to_utc_datetime(d: date) -> datetime:
    """Store date-only values as 00:00:00 UTC for MongoDB Date fields."""
    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)


def to_date(dt: datetime) -> date:
    """Convert MongoDB Date (datetime) back to Python date."""
    if dt.tzinfo is None:
        # assume UTC if naive
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


# ------------------------------
# Data classes for typed returns
# ------------------------------

@dataclass
class Prediction:
    predicted_start: date
    predicted_end: Optional[date]
    avg_cycle_length_days: int
    avg_period_length_days: Optional[int]

@dataclass
class OvulationWindow:
    ovulation_day: date
    fertile_start: date
    fertile_end: date
    luteal_phase_days: int


# ------------------------------
# Main repository layer
# ------------------------------

class PeriodTrackerRepository:
    def __init__(self, mongo_uri: str, db_name: str = "flowcare"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]

        # Collections
        self.users = self.db["users"]  # optional if you sync with Django auth via user_id
        self.preferences = self.db["period_preferences"]
        self.cycles = self.db["period_cycles"]
        self.daily_logs = self.db["daily_logs"]
        self.reminders = self.db["reminders"]

        self._ensure_schema_and_indexes()

    # ------------------------------
    # Setup: validators + indexes
    # ------------------------------
    def _ensure_schema_and_indexes(self):
        # JSON Schema validators (created via collMod so it's safe to call repeatedly)
        # Mongo Atlas/Server 3.6+ supports $jsonSchema.
        # If the collection doesn't exist, create it with validator.
        
        def create_with_validator(name: str, validator: Dict[str, Any]):
            if name not in self.db.list_collection_names():
                # create collection with validator
                self.db.create_collection(name, validator={"$jsonSchema": validator})
            else:
                # Apply/merge validator if collection already exists
                try:
                    self.db.command({
                        "collMod": name,
                        "validator": {"$jsonSchema": validator},
                        "validationLevel": "moderate",
                    })
                except Exception:
                    # collMod may fail on some Mongo setups; ignore to remain compatible
                    pass

        create_with_validator(
            "period_preferences",
            {
                "bsonType": "object",
                "required": ["user_id"],
                "properties": {
                    "user_id": {"bsonType": ["string", "int", "objectId"]},
                    "avg_cycle_length_days": {"bsonType": ["int", "null"], "minimum": 15, "maximum": 90},
                    "avg_period_length_days": {"bsonType": ["int", "null"], "minimum": 1, "maximum": 10},
                    "luteal_phase_days": {"bsonType": ["int", "null"], "minimum": 8, "maximum": 20},
                    "updated_at": {"bsonType": "date"},
                },
                "additionalProperties": True,
            },
        )

        create_with_validator(
            "period_cycles",
            {
                "bsonType": "object",
                "required": ["user_id", "start_date"],
                "properties": {
                    "user_id": {"bsonType": ["string", "int", "objectId"]},
                    "start_date": {"bsonType": "date"},
                    "end_date": {"bsonType": ["date", "null"]},
                    # cycle_length_days is the length of the cycle THAT ENDED on start_date
                    # i.e., difference between THIS start_date and PREVIOUS start_date.
                    "cycle_length_days": {"bsonType": ["int", "null"], "minimum": 10, "maximum": 120},
                    "period_length_days": {"bsonType": ["int", "null"], "minimum": 1, "maximum": 15},
                    "notes": {"bsonType": ["string", "null"]},
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"},
                },
                "additionalProperties": True,
            },
        )

        create_with_validator(
            "daily_logs",
            {
                "bsonType": "object",
                "required": ["user_id", "log_date"],
                "properties": {
                    "user_id": {"bsonType": ["string", "int", "objectId"]},
                    "log_date": {"bsonType": "date"},
                    "mood": {"bsonType": ["string", "null"]},
                    "flow": {"bsonType": ["string", "null"]},  # none, light, medium, heavy
                    "symptoms": {"bsonType": ["array", "null"], "items": {"bsonType": "string"}},
                    "notes": {"bsonType": ["string", "null"]},
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"},
                },
                "additionalProperties": True,
            },
        )

        create_with_validator(
            "reminders",
            {
                "bsonType": "object",
                "required": ["user_id", "remind_at", "type"],
                "properties": {
                    "user_id": {"bsonType": ["string", "int", "objectId"]},
                    "type": {"bsonType": "string"},  # e.g., 'upcoming_period'
                    "remind_at": {"bsonType": "date"},
                    "payload": {"bsonType": ["object", "null"]},
                    "sent": {"bsonType": "bool"},
                    "created_at": {"bsonType": "date"},
                },
                "additionalProperties": True,
            },
        )

        # Indexes
        try:
            self.preferences.create_index([("user_id", ASCENDING)], unique=True, name="uniq_user_prefs")
            self.cycles.create_index([("user_id", ASCENDING), ("start_date", ASCENDING)], unique=True, name="uniq_user_start")
            self.cycles.create_index([("user_id", ASCENDING), ("created_at", ASCENDING)], name="by_user_created")
            self.daily_logs.create_index([("user_id", ASCENDING), ("log_date", ASCENDING)], name="by_user_logdate")
            self.reminders.create_index([("user_id", ASCENDING), ("remind_at", ASCENDING)], name="by_user_remind_at")
            self.reminders.create_index([("sent", ASCENDING)], name="by_sent")
        except Exception:
            # index creation might raise on restricted hosts — ignore non-fatal errors
            pass

    # ------------------------------
    # 1) USER DATA COLLECTION
    # ------------------------------
    def upsert_preferences(
        self,
        user_id: Any,
        avg_cycle_length_days: Optional[int] = None,
        avg_period_length_days: Optional[int] = None,
        luteal_phase_days: Optional[int] = 14,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "avg_cycle_length_days": avg_cycle_length_days,
            "avg_period_length_days": avg_period_length_days,
            "luteal_phase_days": luteal_phase_days,
            "updated_at": now,
        }
        return self.preferences.find_one_and_update(
            {"user_id": user_id},
            {"$set": doc, "$setOnInsert": {"user_id": user_id}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

    def _ensure_user_row(self, user_id: Any) -> None:
        """Ensure a minimal user row exists in `users` collection for visibility in DB UI."""
        now = datetime.now(timezone.utc)
        try:
            self.users.update_one({"user_id": user_id}, {"$set": {"last_seen": now, "user_id": user_id}}, upsert=True)
        except Exception:
            # non-fatal — we don't want user-row creation to break cycle logging
            pass

    def add_cycle_entry(
        self,
        user_id: Any,
        start: date,
        end: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Insert a new cycle start. Also back-fill the cycle_length_days of the PREVIOUS cycle
        (difference between this start and the previous start).
        If `end` is provided, we store period_length_days for this cycle.
        Returns the inserted cycle document.
        """
        now = datetime.now(timezone.utc)
        start_dt = to_utc_datetime(start)
        end_dt = to_utc_datetime(end) if end else None

        # ensure minimal users row (so you see something in the users collection)
        self._ensure_user_row(user_id)

        # Insert this cycle
        try:
            res = self.cycles.insert_one({
                "user_id": user_id,
                "start_date": start_dt,
                "end_date": end_dt,
                "period_length_days": ((end - start).days + 1) if (end is not None) else None,
                "notes": notes,
                "created_at": now,
                "updated_at": now,
            })
        except DuplicateKeyError:
            raise ValueError("A cycle with this start_date already exists for this user.")

        # Find the previous cycle (the most recent start before this)
        prev = self.cycles.find_one(
            {"user_id": user_id, "start_date": {"$lt": start_dt}},
            sort=[("start_date", -1)],
        )
        if prev:
            # cycle_length for PREVIOUS cycle equals (this_start - prev_start)
            prev_len = (start - to_date(prev["start_date"]))
            cycle_len_days = prev_len.days
            try:
                self.cycles.update_one(
                    {"_id": prev["_id"]},
                    {"$set": {"cycle_length_days": cycle_len_days, "updated_at": now}},
                )
            except Exception:
                # ignore non-fatal update errors
                pass

        # Return the inserted cycle (fresh from DB)
        try:
            inserted = self.cycles.find_one({"_id": res.inserted_id})
            return inserted
        except Exception:
            # fallback: return the doc we tried to insert (without _id)
            return {
                "user_id": user_id,
                "start_date": start_dt,
                "end_date": end_dt,
                "period_length_days": ((end - start).days + 1) if (end is not None) else None,
                "notes": notes,
                "created_at": now,
                "updated_at": now,
            }

    def update_cycle_end(
        self,
        user_id: Any,
        start: date,
        end: date,
    ) -> Dict[str, Any]:
        """Set/Update end date and period_length_days for a cycle that started at `start`."""
        now = datetime.now(timezone.utc)
        start_dt = to_utc_datetime(start)
        end_dt = to_utc_datetime(end)
        result = self.cycles.find_one_and_update(
            {"user_id": user_id, "start_date": start_dt},
            {"$set": {
                "end_date": end_dt,
                "period_length_days": (end - start).days + 1,
                "updated_at": now,
            }},
            return_document=ReturnDocument.AFTER,
        )
        if not result:
            raise ValueError("Cycle to update not found.")
        return result

    def log_daily(
        self,
        user_id: Any,
        log_dt: date,
        mood: Optional[str] = None,
        flow: Optional[str] = None,
        symptoms: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": user_id,
            "log_date": to_utc_datetime(log_dt),
            "mood": mood,
            "flow": flow,
            "symptoms": symptoms or [],
            "notes": notes,
            "created_at": now,
            "updated_at": now,
        }
        # ensure user row exists so DB UI shows the user
        self._ensure_user_row(user_id)
        self.daily_logs.insert_one(doc)
        return doc

    # ------------------------------
    # Helpers for previous + next predictions
    # ------------------------------
    def get_latest_two_cycle_starts(self, user_id: Any) -> List[date]:
        """
        Return up to two most recent start dates for user (newest first) as date objects.
        """
        cursor = self.cycles.find({"user_id": user_id}, sort=[("start_date", -1)], projection={"start_date": 1}).limit(2)
        starts = [to_date(doc["start_date"]) for doc in cursor]
        return starts

    def get_prev_and_predicted(self, user_id: Any) -> Dict[str, Optional[date]]:
        """
        Returns:
        {
            "latest_start": date or None,
            "previous_start": date or None,
            "predicted_next_start": date or None
        }
        """
        starts = self.get_latest_two_cycle_starts(user_id)
        latest = starts[0] if len(starts) >= 1 else None
        previous = starts[1] if len(starts) == 2 else None

        # predicted next uses latest + avg_cycle (prefs or history or default 28)
        predicted = None
        if latest:
            prefs = self._get_preferences(user_id)
            avg_cycle = prefs.get("avg_cycle_length_days") or self._compute_avg_cycle_from_history(user_id) or 28
            predicted = latest + timedelta(days=int(avg_cycle))

        return {
            "latest_start": latest,
            "previous_start": previous,
            "predicted_next_start": predicted,
        }

    # ------------------------------
    # 2) CYCLE PREDICTION ALGORITHM
    # ------------------------------
    def _get_latest_cycle_start(self, user_id: Any) -> Optional[date]:
        last = self.cycles.find_one({"user_id": user_id}, sort=[("start_date", -1)])
        return to_date(last["start_date"]) if last else None

    def _compute_avg_cycle_from_history(self, user_id: Any, window: int = 6) -> Optional[int]:
        """
        Average of the most recent measured cycle_length_days (where we know it), up to `window` cycles.
        Returns an integer number of days, or None if insufficient data.
        """
        cursor = self.cycles.find(
            {"user_id": user_id, "cycle_length_days": {"$ne": None}},
            sort=[("start_date", -1)],
            projection={"cycle_length_days": 1},
            limit=window,
        )
        lengths = [doc["cycle_length_days"] for doc in cursor]
        if not lengths:
            return None
        return int(round(sum(lengths) / len(lengths)))

    def _get_preferences(self, user_id: Any) -> Dict[str, Any]:
        return self.preferences.find_one({"user_id": user_id}) or {}

    def predict_next_period(self, user_id: Any) -> Optional[Prediction]:
        last_start = self._get_latest_cycle_start(user_id)
        if not last_start:
            return None

        prefs = self._get_preferences(user_id)
        avg_cycle = prefs.get("avg_cycle_length_days")
        if not avg_cycle:
            avg_cycle = self._compute_avg_cycle_from_history(user_id) or 28  # sensible default

        predicted_start = last_start + timedelta(days=avg_cycle)

        avg_period_len = prefs.get("avg_period_length_days")
        if avg_period_len:
            predicted_end = predicted_start + timedelta(days=avg_period_len - 1)
        else:
            predicted_end = None

        return Prediction(
            predicted_start=predicted_start,
            predicted_end=predicted_end,
            avg_cycle_length_days=int(avg_cycle),
            avg_period_length_days=int(avg_period_len) if avg_period_len else None,
        )

    # ------------------------------
    # 3) OVULATION & FERTILITY WINDOW
    # ------------------------------
    def predict_ovulation(self, user_id: Any) -> Optional[OvulationWindow]:
        pred = self.predict_next_period(user_id)
        if not pred:
            return None
        prefs = self._get_preferences(user_id)
        luteal = prefs.get("luteal_phase_days", 14) or 14
        ovulation_day = pred.predicted_start - timedelta(days=luteal)
        fertile_start = ovulation_day - timedelta(days=5)
        fertile_end = ovulation_day + timedelta(days=5)
        return OvulationWindow(
            ovulation_day=ovulation_day,
            fertile_start=fertile_start,
            fertile_end=fertile_end,
            luteal_phase_days=luteal,
        )

    # ------------------------------
    # 4) TRACKING & NOTIFICATIONS
    # ------------------------------
    def top_preperiod_symptoms(self, user_id: Any, window_days: int = 3, limit: int = 5) -> List[Tuple[str, int]]:
        """
        Simple insight: look at logs within `window_days` BEFORE each *actual* recorded cycle start,
        and return the most frequent symptoms.
        """
        # Get recent cycle starts
        starts = list(self.cycles.find({"user_id": user_id}, sort=[("start_date", -1)], projection={"start_date": 1}).limit(8))
        if not starts:
            return []
        start_dates = [to_utc_datetime(to_date(s["start_date"])) for s in starts]
        earliest = min(start_dates)

        # Pull logs from earliest-window_days .. latest start
        logs = list(self.daily_logs.find({
            "user_id": user_id,
            "log_date": {"$gte": earliest - timedelta(days=window_days), "$lte": max(start_dates)}
        }))

        # Count symptoms appearing within window_days before any start_date
        from collections import Counter
        c = Counter()
        for log in logs:
            log_d = log["log_date"].date()
            for start_dt in start_dates:
                delta = (start_dt.date() - log_d).days
                if 0 < delta <= window_days:
                    for s in (log.get("symptoms") or []):
                        c[s.lower()] += 1
                    break
        return c.most_common(limit)

    def schedule_period_reminders(self, user_id: Any) -> List[Dict[str, Any]]:
        """
        Create reminder docs for upcoming predicted period: at -3 days, -1 day, and day 0.
        This just writes records; you can have a cron/Celery/APScheduler job pick up and send.
        """
        pred = self.predict_next_period(user_id)
        if not pred:
            return []
        when = [
            pred.predicted_start - timedelta(days=3),
            pred.predicted_start - timedelta(days=1),
            pred.predicted_start,
        ]
        created = []
        for w in when:
            doc = {
                "user_id": user_id,
                "type": "upcoming_period",
                "remind_at": to_utc_datetime(w),
                "payload": {
                    "message": f"Your period is likely to start around {pred.predicted_start.isoformat()}.",
                },
                "sent": False,
                "created_at": datetime.now(timezone.utc),
            }
            try:
                self.reminders.insert_one(doc)
            except Exception:
                # non-fatal
                pass
            created.append(doc)
        return created

    def due_reminders(self, as_of: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Fetch reminders that are due and not sent yet."""
        now = as_of or datetime.now(timezone.utc)
        return list(self.reminders.find({"sent": False, "remind_at": {"$lte": now}}))

    def mark_reminder_sent(self, reminder_id):
        self.reminders.update_one({"_id": reminder_id}, {"$set": {"sent": True}})


# ------------------------------
# Example usage (run as a script to test locally)
# ------------------------------
if __name__ == "__main__":
    # 0) Connect
    repo = PeriodTrackerRepository(mongo_uri="mongodb://localhost:27017", db_name="flowcare_demo")

    user = "user_123"  # use your Django user id here (string/int/ObjectId)

    # 1) Preferences
    repo.upsert_preferences(user_id=user, avg_cycle_length_days=28, avg_period_length_days=5, luteal_phase_days=14)

    # 2) Add cycles (start + end). Example data
    repo.add_cycle_entry(user, start=date(2025, 7, 11), end=date(2025, 7, 15))
    repo.add_cycle_entry(user, start=date(2025, 8, 8), end=date(2025, 8, 12))
    repo.add_cycle_entry(user, start=date(2025, 9, 5), end=date(2025, 9, 9))  # when we insert this, it back-fills previous cycle length

    # 3) Predict next period
    pred = repo.predict_next_period(user)
    if pred:
        print("Predicted next start:", pred.predicted_start)
        print("Predicted end:", pred.predicted_end)
        print("Using average cycle:", pred.avg_cycle_length_days)

    # 4) Ovulation & fertile window
    ovu = repo.predict_ovulation(user)
    if ovu:
        print("Ovulation day:", ovu.ovulation_day)
        print("Fertile window:", ovu.fertile_start, "to", ovu.fertile_end)

    # 5) Daily logs + insights
    repo.log_daily(user, log_dt=date(2025, 9, 2), mood="tired", symptoms=["fatigue", "cramps"])  # 3 days before 9/5
    repo.log_daily(user, log_dt=date(2025, 9, 3), mood="irritable", symptoms=["fatigue"])  # 2 days before 9/5
    repo.log_daily(user, log_dt=date(2025, 9, 10), mood="okay", symptoms=["bloating"])  # after period start

    print("Top pre-period symptoms:", repo.top_preperiod_symptoms(user))

    # 6) Reminders
    created = repo.schedule_period_reminders(user)
    print("Created reminders:", [ {"remind_at": c["remind_at"], "type": c["type"]} for c in created ])

    due = repo.due_reminders()
    print("Due reminders now:", len(due))

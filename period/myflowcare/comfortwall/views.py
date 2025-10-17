# comfortwall/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.conf import settings
from django.http import JsonResponse

import hashlib

from .models import Post, Report
from .forms import PostForm, ReportForm
from .utils import get_client_ip, hash_ip, generate_delete_token, generate_anon_name


def list_posts(request):
    """
    Show approved posts, paginated.
    """
    posts_qs = Post.objects.filter(is_approved=True).order_by('-created_at')
    paginator = Paginator(posts_qs, 10)  # 10 posts per page
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    return render(request, 'comfortwall/list.html', {'posts': posts})


def create_post(request):
    """
    Create a new anonymous post. Stores session delete token and hashed IP.
    New posts default to is_approved=False (moderation queue).
    """
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)

            # Ensure session exists
            if not request.session.session_key:
                request.session.create()

            # Session ownership + delete token + anon name
            post.session_key = request.session.session_key
            post.delete_token = generate_delete_token(post.session_key)
            post.anon_name = generate_anon_name(post.session_key)

            # IP -> hash (do NOT store raw IP)
            post.ip_hash = hash_ip(get_client_ip(request))

            # Moderation: recommended default is False so moderators review first
            post.is_approved = True

            post.save()

            # store delete token in session so poster can delete later
            request.session['comfort_delete_token'] = post.delete_token

            messages.success(
                request,
                'Thanks — your post has been submitted for review and will appear publicly soon.'
            )
            return redirect('comfortwall:list')
    else:
        form = PostForm()

    return render(request, 'comfortwall/create.html', {'form': form})


@require_POST
def report_post(request):
    """
    Report a post (creates a Report, flags post, increments report count).
    Works for both AJAX (returns JSON) and non-JS (redirects with message).
    """
    post_id = request.POST.get("post_id")
    reason = request.POST.get("reason")
    other_text = request.POST.get("other_text", "").strip()

    if not post_id or not reason:
        if request.headers.get("Accept") == "application/json":
            return JsonResponse({"success": False, "message": "Missing fields."}, status=400)
        messages.error(request, "Missing fields.")
        return redirect("comfortwall:list")

    post = get_object_or_404(Post, id=post_id)

    # create and save report
    r = Report(
        post=post,
        reason=reason,
        other_text=other_text,
        reporter_ip_hash=hash_ip(get_client_ip(request)),
    )
    r.save()

    # update post flags/count
    post.reports_count = post.reports.count()
    post.is_flagged = True
    post.save(update_fields=["reports_count", "is_flagged"])

    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"success": True, "message": "Report submitted. Thank you."})

    messages.success(request, "Thank you. The post has been reported and will be reviewed.")
    return redirect("comfortwall:list")


@require_POST
def delete_post(request, post_id):
    """
    Allow the original browser (session) to delete their post using the delete token
    stored in the session at creation time.
    """
    post = get_object_or_404(Post, id=post_id)
    token = request.session.get('comfort_delete_token')
    if token and token == post.delete_token:
        post.delete()
        messages.success(request, 'Your post was deleted.')
        return redirect('comfortwall:list')

    messages.error(request, 'Unable to delete this post from this browser.')
    return redirect('comfortwall:list')


@require_POST
def like_post(request, post_id):
    """
    Increment like counter for a post.
    """
    post = get_object_or_404(Post, id=post_id)
    post.likes_count += 1
    post.save(update_fields=["likes_count"])
    messages.success(request, "You liked this post ❤️")
    return redirect('comfortwall:list')


@staff_member_required
def moderation_queue(request):
    """
    Moderation view for staff users to approve/delete/flag posts.
    """
    posts = Post.objects.filter(is_approved=False).order_by('-created_at')

    if request.method == 'POST':
        action = request.POST.get('action')
        pid = request.POST.get('post_id')
        p = get_object_or_404(Post, id=pid)

        if action == 'approve':
            p.is_approved = True
            p.is_flagged = False
            p.save()
            messages.success(request, 'Post approved.')
        elif action == 'delete':
            p.delete()
            messages.success(request, 'Post deleted.')
        elif action == 'flag':
            p.is_flagged = True
            p.save()
            messages.success(request, 'Post flagged.')
        else:
            messages.error(request, 'Unknown action.')

        return redirect('comfortwall:moderation')

    return render(request, 'comfortwall/moderation.html', {'posts': posts})

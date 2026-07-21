"""
Distribution Service - Generate shareable content from journeys
"""
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta


def generate_distribution(journey, distribution_type, options=None, request=None):
    """
    Main generator function
    Returns: (content, metadata)
    """
    generators = {
        'twitter': generate_twitter_thread,
        'linkedin': generate_linkedin_post,
        'blog': generate_blog_post,
        'embed': generate_embed_code,
        'portfolio': generate_portfolio_page,
    }
    
    generator = generators.get(distribution_type)
    if not generator:
        raise ValueError(f"Unknown distribution type: {distribution_type}")
    
    content, metadata = generator(journey, options, request=request)
    return content, metadata


def generate_twitter_thread(journey, options=None, request=None):
    """Generate a Twitter/X thread"""
    activities = journey.activities.all().order_by('day_number_field')[:20]
    
    # Build absolute URL if request is provided
    if request:
        journey_url = request.build_absolute_uri(
            reverse('journey_detail', kwargs={'slug': journey.slug})
        )
    else:
        journey_url = journey.get_absolute_url()
    
    thread = f"🧵 How I built {journey.title} in {journey.duration} days\n\n"
    
    for activity in activities:
        emoji = activity.get_icon_for_type() or '📝'
        thread += f"\nDay {activity.day_number_field}: {emoji} {activity.content[:240]}\n"
    
    if activities.count() < journey.duration:
        thread += f"\n\n📊 {journey.get_progress_percentage()}% complete - {len(activities)}/{journey.duration} days logged"
    
    thread += f"\n\n🏁 Follow the journey: {journey_url}"
    
    # Count tweets (split by double newline)
    tweet_count = len([t for t in thread.split('\n\n') if t.strip()])
    
    return thread, {
        'char_count': len(thread),
        'tweet_count': tweet_count,
        'total_days': activities.count()
    }


def generate_linkedin_post(journey, options=None, request=None):
    """Generate a LinkedIn post"""
    activities = journey.activities.all().order_by('day_number_field')
    milestones = activities.filter(activity_type='milestone')[:3]
    
    # Build absolute URL if request is provided
    if request:
        journey_url = request.build_absolute_uri(
            reverse('journey_detail', kwargs={'slug': journey.slug})
        )
    else:
        journey_url = journey.get_absolute_url()
    
    post = f"🚀 Building {journey.title} in Public\n\n"
    post += f"📊 {journey.duration} days, {activities.count()} updates so far\n"
    post += f"👀 {journey.view_count} views, ❤️ {journey.follower_count} followers\n\n"
    
    if milestones:
        post += "🏆 Key Milestones:\n"
        for m in milestones:
            post += f"• Day {m.day_number_field}: {m.content[:100]}\n"
        post += "\n"
    
    post += "💡 Biggest Lessons:\n"
    post += "• Building in public keeps you accountable\n"
    post += "• Share everything, even failures\n"
    post += "• Community feedback is gold\n\n"
    
    post += f"📖 Read the full journey: {journey_url}"
    
    return post, {
        'char_count': len(post),
        'milestones': len(milestones)
    }


def generate_blog_post(journey, options=None, request=None):
    """Generate a Markdown blog post"""
    activities = journey.activities.all().order_by('day_number_field')[:30]
    
    # Build absolute URL if request is provided
    if request:
        journey_url = request.build_absolute_uri(
            reverse('journey_detail', kwargs={'slug': journey.slug})
        )
    else:
        journey_url = journey.get_absolute_url()
    
    md = f"# How I Built {journey.title}\n\n"
    md += f"> {journey.description}\n\n"
    md += f"**Duration:** {journey.duration} days  \n"
    md += f"**Progress:** {journey.get_progress_percentage()}%  \n"
    md += f"**Views:** {journey.view_count}  \n\n"
    md += "---\n\n"
    
    md += "## The Journey\n\n"
    md += f"I documented {journey.duration} days of building {journey.title}. Here's what happened:\n\n"
    
    for activity in activities:
        md += f"### Day {activity.day_number_field}\n\n"
        if activity.title:
            md += f"**{activity.title}**  \n\n"
        md += f"{activity.content}\n\n"
        
        if activity.media_file:
            if request:
                media_url = request.build_absolute_uri(activity.media_file.url)
            else:
                media_url = activity.media_file.url
            md += f"![{activity.title}]({media_url})\n\n"
        
        if activity.hours_spent:
            md += f"⏱️ {activity.hours_spent} hours spent\n\n"
    
    md += "---\n\n"
    md += "## Lessons Learned\n\n"
    md += "Building in public is the best way to stay accountable.\n\n"
    md += "Key takeaways:\n"
    md += "- Share early, share often\n"
    md += "- Your failures are as valuable as your wins\n"
    md += "- The community will help you improve\n\n"
    
    md += f"**Follow along:** [{journey_url}]({journey_url})"
    
    return md, {
        'word_count': len(md.split()),
        'days': activities.count()
    }


def generate_embed_code(journey, options=None, request=None):
    """Generate embed code for websites"""
    progress = journey.get_progress_percentage()
    
    # Build absolute URL if request is provided
    if request:
        journey_url = request.build_absolute_uri(
            reverse('journey_detail', kwargs={'slug': journey.slug})
        )
    else:
        journey_url = journey.get_absolute_url()
    
    embed = f"""<!-- Rallynex Journey Embed -->
<div class="rallynex-journey" style="border:1px solid #e5e7eb;border-radius:12px;padding:24px;max-width:500px;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <span style="font-size:28px;">🚀</span>
        <div>
            <h3 style="margin:0;font-size:18px;font-weight:600;color:#111827;">{journey.title}</h3>
            <p style="margin:0;font-size:13px;color:#6b7280;">by {journey.creator.get_display_name()}</p>
        </div>
    </div>
    
    <p style="color:#4b5563;font-size:14px;margin-bottom:16px;">{journey.description[:120]}</p>
    
    <div style="background:#f3f4f6;border-radius:8px;padding:12px;margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;font-size:13px;color:#4b5563;">
            <span>Progress</span>
            <span style="font-weight:600;">{progress}%</span>
        </div>
        <div style="height:4px;background:#e5e7eb;border-radius:2px;margin-top:4px;">
            <div style="height:100%;width:{progress}%;background:#3b82f6;border-radius:2px;"></div>
        </div>
    </div>
    
    <div style="display:flex;gap:16px;font-size:12px;color:#6b7280;margin-bottom:16px;">
        <span>📊 {journey.activities.count()} updates</span>
        <span>👁️ {journey.view_count} views</span>
        <span>❤️ {journey.follower_count} followers</span>
    </div>
    
    <a href="{journey_url}" style="display:inline-block;background:#3b82f6;color:#fff;padding:8px 20px;border-radius:6px;text-decoration:none;font-size:14px;font-weight:500;">
        Follow this journey →
    </a>
</div>
<script src="https://rallynex.com/embed.js"></script>"""
    
    return embed, {
        'html_size': len(embed),
        'includes_js': True
    }


def generate_portfolio_page(journey, options=None, request=None):
    """Generate a portfolio page"""
    activities = journey.activities.all().order_by('day_number_field')[:10]
    
    # Build absolute URL if request is provided
    if request:
        journey_url = request.build_absolute_uri(
            reverse('journey_detail', kwargs={'slug': journey.slug})
        )
    else:
        journey_url = journey.get_absolute_url()
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{journey.title} | Build in Public</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 720px;
            margin: 0 auto;
            padding: 48px 24px;
            background: #fafafa;
            color: #1f2937;
            line-height: 1.6;
        }}
        .header {{
            text-align: center;
            padding-bottom: 32px;
            border-bottom: 2px solid #e5e7eb;
            margin-bottom: 32px;
        }}
        .header h1 {{
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header .subtitle {{
            font-size: 18px;
            color: #6b7280;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            padding: 24px;
            background: #fff;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            margin-bottom: 32px;
        }}
        .stats .stat {{
            text-align: center;
        }}
        .stats .stat .number {{
            font-size: 24px;
            font-weight: 700;
            color: #111827;
        }}
        .stats .stat .label {{
            font-size: 12px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 4px;
        }}
        .entry {{
            background: #fff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            transition: all 0.2s;
        }}
        .entry:hover {{
            border-color: #3b82f6;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
        }}
        .entry .day {{
            font-size: 12px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }}
        .entry .content {{
            font-size: 16px;
            margin-top: 8px;
            color: #1f2937;
        }}
        .entry .meta {{
            font-size: 13px;
            color: #6b7280;
            margin-top: 8px;
        }}
        .footer {{
            text-align: center;
            padding-top: 32px;
            border-top: 1px solid #e5e7eb;
            margin-top: 32px;
            color: #6b7280;
            font-size: 14px;
        }}
        .footer a {{
            color: #3b82f6;
            text-decoration: none;
        }}
        .footer a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 {journey.title}</h1>
        <p class="subtitle">{journey.description}</p>
        <p style="color:#6b7280;font-size:14px;margin-top:8px;">
            by {journey.creator.get_display_name()}
        </p>
    </div>
    
    <div class="stats">
        <div class="stat">
            <div class="number">{journey.activities.count()}</div>
            <div class="label">Updates</div>
        </div>
        <div class="stat">
            <div class="number">{journey.get_progress_percentage()}%</div>
            <div class="label">Complete</div>
        </div>
        <div class="stat">
            <div class="number">{journey.view_count}</div>
            <div class="label">Views</div>
        </div>
        <div class="stat">
            <div class="number">{journey.follower_count}</div>
            <div class="label">Followers</div>
        </div>
    </div>
    
    <h2 style="font-size:20px;font-weight:600;margin-bottom:16px;">📖 The Journey</h2>
    
    {''.join([
        f'''<div class="entry">
            <div class="day">Day {a.day_number_field} · {a.get_activity_type_display()}</div>
            <div class="content">{a.content}</div>
            <div class="meta">{a.get_display_date() or ''}</div>
        </div>''' for a in activities
    ])}
    
    {f'''<p style="text-align:center;color:#6b7280;font-size:14px;margin:16px 0;">
        + {journey.activities.count() - 10} more updates...
    </p>''' if journey.activities.count() > 10 else ''}
    
    <div class="footer">
        <p>📖 <a href="{journey_url}">View the full journey →</a></p>
        <p style="font-size:12px;margin-top:8px;">Generated by Rallynex · Build in Public</p>
    </div>
</body>
</html>"""
    
    return html, {
        'html_size': len(html),
        'entries_shown': min(10, activities.count())
    }
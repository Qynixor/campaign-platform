"""
AI Report Service - Generate instant progress reports
"""
from django.utils import timezone
from datetime import timedelta
from ..models import Activity


def generate_instant_report(journey, request=None):
    """
    Generate a simple instant report without heavy AI processing
    Returns: (report_data, metadata)
    """
    activities = journey.activities.all().order_by('day_number_field')
    total_days = journey.duration
    completed_days = activities.count()
    current_day = journey.get_current_day()
    
    # ============================================
    # 1. ANALYTICS
    # ============================================
    completion_rate = round((completed_days / total_days) * 100) if total_days > 0 else 0
    streak = calculate_streak(activities)
    
    # Activity types breakdown
    activity_types = {}
    for activity in activities:
        if activity.activity_type:
            type_display = dict(Activity.ACTIVITY_TYPES).get(activity.activity_type, activity.activity_type)
            activity_types[type_display] = activity_types.get(type_display, 0) + 1
    
    # Mood distribution (if available)
    mood_distribution = {}
    for activity in activities:
        if activity.custom_metrics and 'mood' in activity.custom_metrics:
            mood = activity.custom_metrics['mood']
            mood_distribution[mood] = mood_distribution.get(mood, 0) + 1
    
    analytics = {
        'Completion Rate': f"{completion_rate}%",
        'Days Completed': completed_days,
        'Total Days': total_days,
        'Current Streak': f"{streak} days",
        'Total Entries': completed_days,
        'Activity Types': len(activity_types),
        'Views': journey.view_count,
        'Followers': journey.follower_count,
    }
    
    # ============================================
    # 2. CHARTS / PROGRESS DATA
    # ============================================
    progress_data = generate_progress_chart(activities, journey, current_day)
    
    # ============================================
    # 3. INSIGHTS
    # ============================================
    insights = generate_quick_insights(journey, activities, completion_rate, streak)
    
    # ============================================
    # 4. RECOMMENDATIONS
    # ============================================
    recommendations = generate_recommendations(journey, activities, completion_rate, streak)
    
    # ============================================
    # 5. METRICS SUMMARY
    # ============================================
    metrics = {
        'completion_rate': completion_rate,
        'streak': streak,
        'total_entries': completed_days,
        'view_count': journey.view_count,
        'follower_count': journey.follower_count,
        'activity_types': activity_types,
        'mood_distribution': mood_distribution,
    }
    
    # Build report content
    report_content = build_report_content(journey, analytics, progress_data, insights, recommendations)
    
    # Build summary
    summary = f"""
📊 **Progress Summary**

• {completion_rate}% complete ({completed_days}/{total_days} days)
• 🔥 {streak} day streak
• 👀 {journey.view_count} views
• ❤️ {journey.follower_count} followers
• 📝 {completed_days} entries logged

{insights[0] if insights else ''}
    """.strip()
    
    return {
        'analytics': analytics,
        'insights': {'analytics': analytics},
        'recommendations': recommendations,
        'metrics': metrics,
        'progress_data': progress_data,
        'summary': summary,
        'report_content': report_content,
    }, {
        'completion_rate': completion_rate,
        'streak': streak,
        'total_entries': completed_days,
    }


def calculate_streak(activities):
    """Calculate current streak of consecutive days with entries"""
    if not activities:
        return 0
    
    days = sorted(set(activities.values_list('day_number_field', flat=True)))
    if not days:
        return 0
    
    # Count from the last day backwards
    streak = 1
    for i in range(len(days) - 1, 0, -1):
        if days[i] - days[i-1] == 1:
            streak += 1
        else:
            break
    
    return streak


def generate_progress_chart(activities, journey, current_day):
    """Generate a simple text-based progress chart"""
    completed_days = set(activities.values_list('day_number_field', flat=True))
    
    # Create a visual progress bar
    bar_length = 30
    completed = len(completed_days)
    filled = int((completed / journey.duration) * bar_length) if journey.duration > 0 else 0
    bar = '█' * filled + '░' * (bar_length - filled)
    
    chart = f"""
📈 **Progress Chart**

[{bar}]
{completed}/{journey.duration} days completed ({round((completed/journey.duration)*100) if journey.duration > 0 else 0}%)

📅 **Recent Activity:**
"""
    
    # Show last 7 days
    recent_days = []
    for day in range(max(1, current_day - 6), current_day + 1):
        status = "✅" if day in completed_days else "⬜"
        recent_days.append(f"Day {day}: {status}")
    
    chart += "\n".join(recent_days)
    
    return chart


def generate_quick_insights(journey, activities, completion_rate, streak):
    """Generate quick insights without AI"""
    insights = []
    
    if activities.count() == 0:
        return ["🌟 Start your journey by adding your first entry!"]
    
    # Progress insight
    if completion_rate >= 100:
        insights.append("🎉 **Congratulations!** You've completed your journey!")
    elif completion_rate >= 75:
        insights.append("🚀 **Almost there!** You're in the final stretch!")
    elif completion_rate >= 50:
        insights.append("💪 **Halfway there!** Keep up the momentum!")
    elif completion_rate >= 25:
        insights.append("📈 **Great start!** Consistency is key!")
    else:
        insights.append("🌟 **Every journey starts with a single step.** Keep building!")
    
    # Streak insight
    if streak >= 7:
        insights.append(f"🔥 **Amazing!** You're on a {streak}-day streak! Keep it going!")
    elif streak >= 3:
        insights.append(f"💪 **Nice!** {streak}-day streak! Stay consistent!")
    elif streak >= 1 and activities.count() > 0:
        insights.append("📝 **You're building momentum!** Try to post daily!")
    
    # Activity type insight
    activity_types = {}
    for activity in activities:
        if activity.activity_type:
            type_display = dict(Activity.ACTIVITY_TYPES).get(activity.activity_type, activity.activity_type)
            activity_types[type_display] = activity_types.get(type_display, 0) + 1
    
    if activity_types:
        most_common = max(activity_types, key=activity_types.get)
        insights.append(f"📊 **Most common activity:** {most_common}")
    
    return insights


def generate_recommendations(journey, activities, completion_rate, streak):
    """Generate simple recommendations"""
    recommendations = []
    
    if activities.count() == 0:
        return ["📝 **Add your first entry** to start tracking your progress!"]
    
    # Consistency recommendations
    if completion_rate < 30:
        recommendations.append("📝 **Try to post daily** to build consistency. Even small updates count!")
    
    if streak < 3 and activities.count() > 0:
        recommendations.append("🔥 **Build a streak!** Try to post for 7 days in a row.")
    
    # Progress recommendations
    if completion_rate >= 50 and completion_rate < 75:
        recommendations.append("🚀 **You're halfway there!** Focus on the next milestone.")
    
    if completion_rate >= 75 and completion_rate < 100:
        recommendations.append("🏁 **Final stretch!** Keep pushing to complete your journey!")
    
    if completion_rate >= 100:
        recommendations.append("🎉 **Journey complete!** Celebrate your achievement and reflect on what you've learned.")
    
    # If no recommendations, add a positive one
    if not recommendations:
        recommendations.append("🎉 **You're doing great!** Keep building in public and sharing your journey!")
    
    return recommendations


def build_report_content(journey, analytics, progress_data, insights, recommendations):
    """Build the full report content as HTML/markdown"""
    
    content = f"""
# 📊 Progress Report: {journey.title}

---

## 📈 Analytics

| Metric | Value |
|--------|-------|
"""
    
    for key, value in analytics.items():
        content += f"| {key} | {value} |\n"
    
    content += f"""
---

## 📊 Progress Chart

{progress_data}

---

## 💡 Key Insights

"""
    
    for insight in insights:
        content += f"- {insight}\n"
    
    content += f"""
---

## 🎯 Recommendations

"""
    
    for rec in recommendations:
        content += f"- {rec}\n"
    
    content += f"""
---

*Report generated on {timezone.now().strftime('%B %d, %Y at %I:%M %p')}*
*Journey: {journey.title}*
    """
    
    return content
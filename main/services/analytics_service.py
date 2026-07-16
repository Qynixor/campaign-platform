# main/services/analytics_service.py

from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from datetime import timedelta
import json

class AnalyticsService:
    """Service for generating journey analytics"""
    
    @staticmethod
    def get_journey_analytics(journey):
        """Generate comprehensive analytics for a journey"""
        activities = journey.activities.all().order_by('day_number_field')
        
        # ===== BASIC STATS =====
        total_entries = activities.count()
        total_days = journey.duration
        completion_rate = (total_entries / total_days * 100) if total_days > 0 else 0
        
        # ===== MOOD ANALYSIS =====
        mood_counts = {}
        mood_trend = []
        for activity in activities:
            if activity.mood:
                mood_counts[activity.mood] = mood_counts.get(activity.mood, 0) + 1
                mood_trend.append({
                    'day': activity.day_number_field,
                    'mood': activity.mood
                })
        
        # ===== ACTIVITY TYPES =====
        activity_types = {}
        for activity in activities:
            if activity.activity_type:
                activity_types[activity.activity_type] = activity_types.get(activity.activity_type, 0) + 1
        
        # ===== INTENSITY DISTRIBUTION =====
        intensity_counts = {}
        for activity in activities:
            if activity.intensity:
                intensity_counts[activity.intensity] = intensity_counts.get(activity.intensity, 0) + 1
        
        # ===== DURATION STATS =====
        durations = [a.duration_minutes for a in activities if a.duration_minutes]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        
        # ===== STREAK CALCULATION =====
        streak = AnalyticsService._calculate_streak(activities)
        
        # ===== ACTIVITY PATTERN =====
        # Check if user is consistent (entries every day vs gaps)
        days_with_activity = set([a.day_number_field for a in activities])
        consistency = len(days_with_activity) / total_days * 100 if total_days > 0 else 0
        
        # ===== METRICS TRENDS (from progress_metrics JSON) =====
        metrics_data = {}
        for activity in activities:
            if activity.progress_metrics:
                for key, value in activity.progress_metrics.items():
                    if key not in metrics_data:
                        metrics_data[key] = []
                    metrics_data[key].append({
                        'day': activity.day_number_field,
                        'value': value
                    })
        
        # ===== GENERATE INSIGHTS =====
        insights = AnalyticsService._generate_insights(
            completion_rate, streak, activity_types, mood_counts, consistency
        )
        
        # ===== GENERATE RECOMMENDATIONS =====
        recommendations = AnalyticsService._generate_recommendations(
            completion_rate, streak, activity_types, mood_counts
        )
        
        return {
            'total_entries': total_entries,
            'completion_rate': round(completion_rate, 1),
            'mood_distribution': mood_counts,
            'mood_trend': mood_trend,
            'activity_types': activity_types,
            'intensity_distribution': intensity_counts,
            'avg_duration': round(avg_duration, 1),
            'max_duration': max_duration,
            'min_duration': min_duration,
            'current_streak': streak,
            'consistency': round(consistency, 1),
            'metrics_data': metrics_data,
            'insights': insights,
            'recommendations': recommendations,
        }
    
    @staticmethod
    def _calculate_streak(activities):
        """Calculate current streak of consecutive days"""
        if not activities:
            return 0
        
        days = sorted(set([a.day_number_field for a in activities]))
        if not days:
            return 0
        
        # Check from most recent day backwards
        current_day = days[-1]
        streak = 0
        
        # Count backwards from the last day
        for i in range(len(days) - 1, -1, -1):
            if days[i] == current_day - (len(days) - 1 - i):
                streak += 1
            else:
                break
        
        return streak
    
    @staticmethod
    def _generate_insights(completion_rate, streak, activity_types, mood_counts, consistency):
        """Generate key insights from data"""
        insights = []
        
        # Progress insight
        if completion_rate >= 80:
            insights.append("🌟 Excellent progress! You're consistently showing up.")
        elif completion_rate >= 50:
            insights.append("💪 Good progress! Keep building momentum.")
        else:
            insights.append("📈 Start building consistency. Every day counts!")
        
        # Streak insight
        if streak >= 7:
            insights.append(f"🔥 Amazing {streak}-day streak! You're building powerful habits.")
        elif streak >= 3:
            insights.append(f"💪 {streak}-day streak! Keep going, you're doing great.")
        elif streak > 0:
            insights.append(f"✅ {streak}-day streak started. Consistency is the key!")
        
        # Activity variety insight
        if len(activity_types) >= 3:
            insights.append("🎯 Great variety in your activities! This keeps things interesting.")
        elif len(activity_types) >= 2:
            insights.append("🏋️ Consider trying different types of activities for better results.")
        
        # Mood insight
        if mood_counts:
            positive_moods = ['amazing', 'great', 'good', 'proud', 'grateful']
            positive_count = sum(count for mood, count in mood_counts.items() if mood in positive_moods)
            total = sum(mood_counts.values())
            if total > 0 and (positive_count / total) >= 0.7:
                insights.append("😊 Your mood is consistently positive. Great mindset!")
            elif total > 0 and (positive_count / total) <= 0.3:
                insights.append("💪 Consider adding rest days or lighter activities to manage fatigue.")
        
        return insights
    
    @staticmethod
    def _generate_recommendations(completion_rate, streak, activity_types, mood_counts):
        """Generate actionable recommendations"""
        recommendations = []
        
        # Progress recommendations
        if completion_rate < 30:
            recommendations.append("Start with short, manageable workouts (15-20 min) to build consistency.")
        elif completion_rate < 60:
            recommendations.append("Try to increase your activity duration by 5-10 minutes each week.")
        else:
            recommendations.append("Challenge yourself with new goals or increase intensity.")
        
        # Streak recommendations
        if streak < 3:
            recommendations.append("Set a goal to exercise for 7 consecutive days to build a habit.")
        
        # Activity variety
        if len(activity_types) <= 2:
            recommendations.append("Try a new activity this week to keep your routine fresh.")
        
        # Mood-based recommendations
        if mood_counts:
            negative_moods = ['struggling', 'tired', 'okay']
            negative_count = sum(count for mood, count in mood_counts.items() if mood in negative_moods)
            total = sum(mood_counts.values())
            if total > 0 and (negative_count / total) > 0.3:
                recommendations.append("Consider adding yoga or stretching to your routine for recovery.")
        
        # If no recommendations generated, add default
        if not recommendations:
            recommendations.append("Keep up the great work! You're on the right track.")
        
        return recommendations
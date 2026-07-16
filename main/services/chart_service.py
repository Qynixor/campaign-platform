# main/services/chart_service.py

import json
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta

class ChartService:
    """Service for generating chart data"""
    
    @staticmethod
    def get_progress_chart_data(journey):
        """Generate data for progress charts"""
        activities = journey.activities.all().order_by('day_number_field')
        
        chart_data = {
            'labels': [],
            'datasets': []
        }
        
        if not activities:
            return chart_data
        
        # ===== COMPLETION CHART =====
        completion_data = []
        for day in range(1, journey.duration + 1):
            activity = journey.get_activity_for_day(day)
            completion_data.append(1 if activity else 0)
            chart_data['labels'].append(f'Day {day}')
        
        chart_data['datasets'].append({
            'label': 'Entries',
            'data': completion_data,
            'backgroundColor': 'rgba(59, 130, 246, 0.5)',
            'borderColor': '#3B82F6',
            'borderWidth': 2,
            'fill': True,
            'tension': 0.3
        })
        
        # ===== MOOD TREND =====
        mood_values = {
            'amazing': 5,
            'great': 4,
            'good': 3,
            'okay': 2,
            'tired': 1,
            'challenged': 3,
            'struggling': 0,
            'proud': 5,
            'grateful': 4,
            'neutral': 2
        }
        
        mood_data = []
        mood_labels = []
        for activity in activities:
            mood_data.append(mood_values.get(activity.mood, 0))
            mood_labels.append(f'Day {activity.day_number_field}')
        
        if mood_data:
            chart_data['datasets'].append({
                'label': 'Mood',
                'data': mood_data,
                'backgroundColor': 'rgba(16, 185, 129, 0.3)',
                'borderColor': '#10B981',
                'borderWidth': 2,
                'fill': True,
                'tension': 0.4,
                'pointBackgroundColor': '#10B981',
                'pointBorderColor': '#fff',
                'pointBorderWidth': 2,
                'pointRadius': 4
            })
        
        # ===== DURATION TREND =====
        duration_data = []
        for activity in activities:
            duration_data.append(activity.duration_minutes or 0)
        
        if any(duration_data):
            chart_data['datasets'].append({
                'label': 'Duration (min)',
                'data': duration_data,
                'backgroundColor': 'rgba(139, 92, 246, 0.3)',
                'borderColor': '#8B5CF6',
                'borderWidth': 2,
                'fill': True,
                'tension': 0.3,
                'pointBackgroundColor': '#8B5CF6',
                'pointBorderColor': '#fff',
                'pointBorderWidth': 2,
                'pointRadius': 4
            })
        
        return chart_data
    
    @staticmethod
    def get_metrics_chart_data(journey, metric_key):
        """Generate chart data for a specific metric"""
        activities = journey.activities.filter(
            custom_metrics__has_key=metric_key
        ).order_by('day_number_field')
        
        if not activities:
            return None
        
        data = []
        for activity in activities:
            value = activity.custom_metrics.get(metric_key)
            if value is not None:
                data.append({
                    'day': activity.day_number_field,
                    'value': float(value) if isinstance(value, (int, float)) else value
                })
        
        return {
            'labels': [f'Day {d["day"]}' for d in data],
            'data': [d['value'] for d in data],
            'metric': metric_key
        }
    
    @staticmethod
    def get_distribution_data(journey):
        """Get distribution data for charts"""
        activities = journey.activities.all()
        
        # Mood distribution
        mood_counts = {}
        for activity in activities:
            if activity.mood:
                mood_counts[activity.mood] = mood_counts.get(activity.mood, 0) + 1
        
        # Activity type distribution
        activity_counts = {}
        for activity in activities:
            if activity.activity_type:
                activity_counts[activity.activity_type] = activity_counts.get(activity.activity_type, 0) + 1
        
        # Intensity distribution
        intensity_counts = {}
        for activity in activities:
            if activity.intensity:
                intensity_counts[activity.intensity] = intensity_counts.get(activity.intensity, 0) + 1
        
        return {
            'mood': mood_counts,
            'activity_types': activity_counts,
            'intensity': intensity_counts
        }
    
    @staticmethod
    def get_streak_data(journey):
        """Get streak data for chart"""
        activities = journey.activities.all().order_by('day_number_field')
        
        if not activities:
            return {'labels': [], 'data': []}
        
        # Calculate running streak
        streak_data = []
        current_streak = 0
        
        for day in range(1, journey.duration + 1):
            activity = journey.get_activity_for_day(day)
            if activity:
                current_streak += 1
            else:
                current_streak = 0
            streak_data.append({
                'day': day,
                'streak': current_streak
            })
        
        return {
            'labels': [f'Day {d["day"]}' for d in streak_data],
            'data': [d['streak'] for d in streak_data]
        }
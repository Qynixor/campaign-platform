# main/services/metrics_service.py

from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
import json

class MetricsService:
    """Service for handling custom metrics"""
    
    # Pre-defined metric types with labels and units
    METRIC_TYPES = {
        'weight': {'label': 'Weight', 'unit': 'kg', 'icon': '⚖️', 'color': '#3B82F6'},
        'sleep': {'label': 'Sleep', 'unit': 'hours', 'icon': '😴', 'color': '#8B5CF6'},
        'mood': {'label': 'Mood', 'unit': 'score', 'icon': '😊', 'color': '#10B981'},
        'energy': {'label': 'Energy', 'unit': 'score', 'icon': '⚡', 'color': '#F59E0B'},
        'stress': {'label': 'Stress', 'unit': 'score', 'icon': '😰', 'color': '#EF4444'},
        'water': {'label': 'Water', 'unit': 'glasses', 'icon': '💧', 'color': '#3B82F6'},
        'steps': {'label': 'Steps', 'unit': 'steps', 'icon': '👣', 'color': '#8B5CF6'},
        'calories': {'label': 'Calories', 'unit': 'kcal', 'icon': '🔥', 'color': '#F59E0B'},
        'heart_rate': {'label': 'Heart Rate', 'unit': 'bpm', 'icon': '❤️', 'color': '#EF4444'},
        'meditation': {'label': 'Meditation', 'unit': 'minutes', 'icon': '🧘', 'color': '#10B981'},
    }
    
    @staticmethod
    def get_user_metrics(user):
        """Get all metrics tracked by a user"""
        activities = Activity.objects.filter(
            journey__creator=user.profile
        ).exclude(custom_metrics={})
        
        tracked_metrics = set()
        for activity in activities:
            if activity.custom_metrics:
                tracked_metrics.update(activity.custom_metrics.keys())
        
        return sorted(list(tracked_metrics))
    
    @staticmethod
    def get_metric_data(journey, metric_key):
        """Get all data for a specific metric in a journey"""
        activities = journey.activities.filter(
            custom_metrics__has_key=metric_key
        ).order_by('day_number_field')
        
        data = []
        for activity in activities:
            value = activity.custom_metrics.get(metric_key)
            if value is not None:
                data.append({
                    'day': activity.day_number_field,
                    'value': float(value) if isinstance(value, (int, float)) else value,
                    'date': activity.created_at,
                    'activity_id': activity.id
                })
        
        return data
    
    @staticmethod
    def get_metric_stats(journey, metric_key):
        """Get statistics for a specific metric"""
        data = MetricsService.get_metric_data(journey, metric_key)
        
        if not data:
            return None
        
        values = [d['value'] for d in data if isinstance(d['value'], (int, float))]
        
        if not values:
            return {
                'count': len(data),
                'latest': data[-1]['value'] if data else None,
                'first': data[0]['value'] if data else None,
            }
        
        return {
            'count': len(data),
            'latest': data[-1]['value'] if data else None,
            'first': data[0]['value'] if data else None,
            'min': min(values),
            'max': max(values),
            'avg': round(sum(values) / len(values), 2),
            'total': sum(values),
            'trend': MetricsService._calculate_trend(values),
            'change': round((values[-1] - values[0]), 2) if len(values) > 1 else 0
        }
    
    @staticmethod
    def _calculate_trend(values):
        """Calculate trend direction"""
        if len(values) < 2:
            return 'stable'
        
        # Simple linear trend
        first = values[0]
        last = values[-1]
        
        if last > first * 1.05:
            return 'increasing'
        elif last < first * 0.95:
            return 'decreasing'
        else:
            return 'stable'
    
    @staticmethod
    def get_metric_summary(journey):
        """Get summary of all metrics for a journey"""
        activities = journey.activities.exclude(custom_metrics={})
        
        if not activities:
            return {}
        
        all_metrics = {}
        for activity in activities:
            if activity.custom_metrics:
                for key, value in activity.custom_metrics.items():
                    if key not in all_metrics:
                        all_metrics[key] = []
                    all_metrics[key].append({
                        'day': activity.day_number_field,
                        'value': value
                    })
        
        summary = {}
        for key, data in all_metrics.items():
            values = [d['value'] for d in data if isinstance(d['value'], (int, float))]
            metric_info = MetricsService.METRIC_TYPES.get(key, {})
            
            summary[key] = {
                'label': metric_info.get('label', key.title()),
                'unit': metric_info.get('unit', ''),
                'icon': metric_info.get('icon', '📊'),
                'color': metric_info.get('color', '#3B82F6'),
                'count': len(data),
                'latest': data[-1]['value'] if data else None,
                'change': round((values[-1] - values[0]), 2) if len(values) > 1 else 0 if values else 0,
                'avg': round(sum(values) / len(values), 2) if values else 0,
                'min': min(values) if values else 0,
                'max': max(values) if values else 0,
            }
        
        return summary
    
    @staticmethod
    def get_metric_chart_data(journey, metric_key, days=None):
        """Get data formatted for chart display"""
        data = MetricsService.get_metric_data(journey, metric_key)
        
        if days:
            # Filter to last N days
            data = data[-days:]
        
        return {
            'labels': [f'Day {d["day"]}' for d in data],
            'values': [d['value'] for d in data],
            'metric': metric_key,
            'info': MetricsService.METRIC_TYPES.get(metric_key, {})
        }
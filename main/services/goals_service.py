# main/services/goals_service.py

from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q

class GoalsService:
    """Service for handling goals and milestones"""
    
    @staticmethod
    def get_journey_goals(journey):
        """Get all goals for a journey"""
        return journey.goals.all().order_by('-created_at')
    
    @staticmethod
    def get_active_goals(journey):
        """Get active (not completed) goals"""
        return journey.goals.filter(is_completed=False).order_by('deadline')
    
    @staticmethod
    def get_completed_goals(journey):
        """Get completed goals"""
        return journey.goals.filter(is_completed=True).order_by('-completed_at')
    
    @staticmethod
    def get_journey_milestones(journey):
        """Get all milestones for a journey"""
        return journey.milestones.all().order_by('-achieved_at')
    
    @staticmethod
    def check_milestones(journey, user):
        """Check and create milestones for a journey"""
        activities = journey.activities.all()
        total_entries = activities.count()
        current_day = journey.get_current_day()
        
        milestones_created = []
        
        # Check first entry
        if total_entries >= 1:
            milestones_created.extend(
                GoalsService._create_milestone_if_not_exists(
                    user, journey, 'first_entry', 'First Entry', '🎉'
                )
            )
        
        # Check streaks
        streak = GoalsService._calculate_streak(activities)
        if streak >= 3:
            milestones_created.extend(
                GoalsService._create_milestone_if_not_exists(
                    user, journey, 'streak_3', '3-Day Streak', '🔥'
                )
            )
        if streak >= 7:
            milestones_created.extend(
                GoalsService._create_milestone_if_not_exists(
                    user, journey, 'streak_7', '7-Day Streak', '⚡'
                )
            )
        if streak >= 14:
            milestones_created.extend(
                GoalsService._create_milestone_if_not_exists(
                    user, journey, 'streak_14', '14-Day Streak', '🌟'
                )
            )
        if streak >= 30:
            milestones_created.extend(
                GoalsService._create_milestone_if_not_exists(
                    user, journey, 'streak_30', '30-Day Streak', '👑'
                )
            )
        
        # Check halfway
        if journey.duration > 0 and current_day >= journey.duration / 2:
            milestones_created.extend(
                GoalsService._create_milestone_if_not_exists(
                    user, journey, 'halfway', 'Halfway Point', '🏁'
                )
            )
        
        # Check complete
        if journey.is_archived or current_day >= journey.duration:
            milestones_created.extend(
                GoalsService._create_milestone_if_not_exists(
                    user, journey, 'complete', 'Journey Complete', '🎯'
                )
            )
        
        return milestones_created
    
    @staticmethod
    def _create_milestone_if_not_exists(user, journey, milestone_type, name, icon):
        """Create a milestone if it doesn't exist"""
        milestone, created = Milestone.objects.get_or_create(
            user=user,
            journey=journey,
            milestone_type=milestone_type,
            defaults={
                'name': name,
                'icon': icon,
                'description': f"Achieved {name} in {journey.title}",
                'achieved_at': timezone.now()
            }
        )
        return [milestone] if created else []
    
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
        streak = 1
        
        # Count backwards from the last day
        for i in range(len(days) - 2, -1, -1):
            if days[i] == days[i+1] - 1:
                streak += 1
            else:
                break
        
        return streak
    
    @staticmethod
    def create_goal(user, journey, goal_type, target_value, title, unit='', description='', deadline=None):
        """Create a new goal"""
        goal = Goal.objects.create(
            user=user,
            journey=journey,
            goal_type=goal_type,
            target_value=target_value,
            unit=unit,
            title=title,
            description=description,
            deadline=deadline
        )
        return goal
    
    @staticmethod
    def get_goal_stats(journey):
        """Get statistics about goals"""
        total_goals = journey.goals.count()
        completed_goals = journey.goals.filter(is_completed=True).count()
        active_goals = journey.goals.filter(is_completed=False).count()
        
        return {
            'total': total_goals,
            'completed': completed_goals,
            'active': active_goals,
            'completion_rate': round((completed_goals / total_goals) * 100) if total_goals > 0 else 0
        }
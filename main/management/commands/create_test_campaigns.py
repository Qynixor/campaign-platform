# main/management/commands/create_test_campaigns.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random
from main.models import Campaign, Profile, Love, CampaignFollow, Activity

class Command(BaseCommand):
    help = 'Creates test campaigns for development'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating test campaigns...')
        
        # Create a test user if none exists
        test_user = self.get_or_create_test_user()
        
        # Campaign titles by category
        campaign_data = {
            'Personal Empowerment': [
                'Women in Tech Mentorship Program',
                'Youth Leadership Bootcamp',
                'Confidence Building Workshop for Teens',
                'Public Speaking Mastery Course',
                'Personal Development Coaching',
                'Empowerment Through Storytelling',
                'Self-Discovery Retreat',
                'Life Skills for Young Adults'
            ],
            'Health & Wellbeing Causes': [
                'Free Yoga for Mental Health',
                'Community Fitness Challenge',
                'Healthy Eating Education Program',
                'Meditation for Beginners',
                'Cancer Survivors Support Group',
                'Mental Health Awareness Campaign',
                'Fitness Equipment for Underprivileged Youth',
                'Holistic Wellness Workshop'
            ],
            'Economic Support & Financial Causes': [
                'Small Business Startup Fund',
                'Financial Literacy for Teens',
                'Microloans for Women Entrepreneurs',
                'Job Training for Unemployed Youth',
                'Emergency Relief Fund for Families',
                'Financial Planning Workshop',
                'Support Local Artisans',
                'Economic Empowerment Program'
            ],
            'Creative & Cultural Causes': [
                'Indigenous Art Preservation',
                'Youth Music Production Studio',
                'Community Mural Project',
                'Traditional Dance Workshop',
                'Photography for Social Change',
                'Creative Writing Circle',
                'Film Making for Beginners',
                'Cultural Heritage Festival'
            ],
            'Mental Health & Emotional Support': [
                'Free Therapy Sessions for Teens',
                'Anxiety Support Group',
                'Mental Health Hotline',
                'Stress Management Workshop',
                'Peer Counseling Training',
                'Mindfulness in Schools',
                'Depression Awareness Campaign',
                'Healing Circle for Trauma Survivors'
            ],
            'Career, Work & Opportunity': [
                'Tech Skills Bootcamp',
                'Resume Writing Workshop',
                'Internship Placement Program',
                'Career Mentorship Network',
                'Professional Development Fund',
                'Networking Events for Young Professionals',
                'Entrepreneurship Incubator',
                'Job Fair for Underrepresented Groups'
            ],
            'Housing, Living & Stability': [
                'Affordable Housing Initiative',
                'Homeless Shelter Support',
                'First-Time Homebuyer Education',
                'Rental Assistance Program',
                'Community Garden Housing Project',
                'Temporary Housing for Families in Crisis',
                'Sustainable Living Workshop',
                'Housing Rights Advocacy'
            ],
            'Community & Social Impact': [
                'Community Clean-up Drive',
                'Food Bank Distribution Network',
                'Neighborhood Watch Program',
                'Youth Center Renovation',
                'Community Garden Project',
                'Local Library Support',
                'Senior Citizen Outreach',
                'Intergenerational Connection Program'
            ],
            'Education & Skill Building': [
                'STEM Education for Girls',
                'After-School Tutoring Program',
                'Scholarship Fund for Underprivileged Students',
                'Digital Literacy for Seniors',
                'Adult Education Classes',
                'School Supplies Drive',
                'Coding Bootcamp for Teens',
                'College Application Assistance'
            ],
            'Exploration, Sports & Challenges': [
                'Mountain Climbing for Charity',
                'Marathon Fundraiser',
                'Youth Sports League',
                'Outdoor Adventure Camp',
                'Bike Across America Challenge',
                'Swimming Lessons for Underprivileged Kids',
                'Extreme Sports for Disability Awareness',
                'Nature Exploration Club'
            ],
            'Religious & Spiritual Causes': [
                'Interfaith Youth Group',
                'Meditation Retreat Center',
                'Community Worship Space Renovation',
                'Spiritual Counseling Services',
                'Religious Education Program',
                'Faith-Based Community Outreach',
                'Pilgrimage Support Fund',
                'Multi-Faith Dialogue Initiative'
            ],
            'Other Causes': [
                'Animal Shelter Support',
                'Environmental Conservation Project',
                'Disaster Relief Fund',
                'Technology Access for Rural Communities',
                'Veterans Support Network',
                'Disability Rights Advocacy',
                'Refugee Assistance Program',
                'LGBTQ+ Youth Support'
            ]
        }
        
        # Create profiles for additional users
        test_profiles = []
        usernames = ['alex_chen', 'maria_rodriguez', 'james_wilson', 'sarah_ahmed', 
                     'david_kim', 'lisa_patel', 'miguel_santos', 'amina_ousmane']
        
        for username in usernames:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'is_active': True
                }
            )
            if created:
                user.set_password('testpass123')
                user.save()
                self.stdout.write(f'  Created user: {username}')
            
            profile, _ = Profile.objects.get_or_create(user=user)
            test_profiles.append(profile)
        
        # Add test_user to profiles list
        test_profiles.append(test_user)
        
        # Create campaigns
        campaigns_created = 0
        now = timezone.now()
        
        for category, titles in campaign_data.items():
            for i, title in enumerate(titles):
                # Randomly select a profile as creator
                creator = random.choice(test_profiles)
                
                # Random timestamp (between 60 days ago and now)
                days_ago = random.randint(0, 60)
                timestamp = now - timedelta(days=days_ago)
                
                # Random duration
                duration = random.choice([7, 14, 30, 60, 90])
                duration_unit = random.choice(['days'])
                
                # Calculate end date
                end_date = timestamp + timedelta(days=duration)
                
                # Random funding goal
                funding_goal = random.choice([1000, 2500, 5000, 10000, 25000, 50000])
                
                # Create campaign
                campaign = Campaign.objects.create(
                    user=creator,
                    title=title,
                    content=f"This is a test campaign for {title}. We're raising funds to support our cause. Join us in making a difference!",
                    category=category,
                    duration=duration,
                    duration_unit=duration_unit,
                    journey_start_date=timestamp,
                    timestamp=timestamp,
                    end_date=end_date,
                    funding_goal=funding_goal,
                    is_active=True
                )
                
                campaigns_created += 1
                
                # Add some loves (random number)
                for _ in range(random.randint(0, 20)):
                    lover = random.choice(test_profiles)
                    try:
                        Love.objects.get_or_create(
                            campaign=campaign,
                            user=lover.user
                        )
                    except:
                        pass
                
                # Add some followers (random number)
                for _ in range(random.randint(0, 15)):
                    follower = random.choice(test_profiles)
                    try:
                        CampaignFollow.objects.get_or_create(
                            campaign=campaign,
                            user=follower.user
                        )
                    except:
                        pass
                
                # Add some activities (random number)
                for day in range(1, min(random.randint(1, duration), 10)):
                    activity_date = timestamp + timedelta(days=day-1)
                    if activity_date <= now:
                        Activity.objects.create(
                            campaign=campaign,
                            content=f"Day {day} update: Making great progress on our campaign!",
                            timestamp=activity_date
                        )
                
                self.stdout.write(f'  Created: {title} ({category})')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {campaigns_created} test campaigns'))
    
    def get_or_create_test_user(self):
        """Get or create a test user account"""
        test_user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'is_active': True
            }
        )
        
        if created:
            test_user.set_password('testpass123')
            test_user.save()
            self.stdout.write('  Created test user: testuser (password: testpass123)')
        
        # Ensure profile exists
        profile, _ = Profile.objects.get_or_create(user=test_user)
        
        return profile
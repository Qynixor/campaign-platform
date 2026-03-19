from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random
from main.models import Profile, Campaign, Donation

User = get_user_model()

class Command(BaseCommand):
    help = 'Create fake supporters for testing'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username of the campaign owner')
        parser.add_argument('--count', type=int, default=5, help='Number of fake supporters to create')

    def handle(self, *args, **options):
        username = options['username']
        count = min(options['count'], 5)  # Max 5 supporters
        
        try:
            # Get the user whose campaigns will receive donations
            user_obj = User.objects.get(username=username)
            profile = Profile.objects.get(user=user_obj)
            
            # Get their campaigns
            campaigns = Campaign.objects.filter(user=profile, is_active=True)
            
            if not campaigns.exists():
                self.stdout.write(self.style.WARNING(f'No campaigns found for {username}'))
                return
            
            # Create fake users
            fake_users_created = 0
            donations_created = 0
            
            first_names = ['Sarah', 'Michael', 'Emma', 'James', 'Olivia']
            last_names = ['Johnson', 'Chen', 'Williams', 'Wilson', 'Brown']
            
            for i in range(count):
                # Create fake user
                fake_username = f"supporter_{i+1}"
                email = f"{fake_username}@example.com"
                
                fake_user, created = User.objects.get_or_create(
                    username=fake_username,
                    defaults={
                        'email': email,
                        'first_name': first_names[i],
                        'last_name': last_names[i],
                    }
                )
                
                if created:
                    fake_user.set_password('testpass123')
                    fake_user.save()
                    
                    # Create profile
                    Profile.objects.get_or_create(user=fake_user)
                    fake_users_created += 1
                
                # Create 1-2 donations for this supporter
                num_donations = random.randint(1, 2)
                
                for j in range(num_donations):
                    # Pick random campaign
                    campaign = random.choice(campaigns)
                    
                    # Random donation amount between $5 and $200
                    amount = round(random.uniform(5, 200), 2)
                    
                    # Random date in the last 3 months
                    days_ago = random.randint(1, 90)
                    donation_date = timezone.now() - timedelta(days=days_ago)
                    
                    # Create donation
                    Donation.objects.create(
                        user=fake_user,
                        campaign=campaign,
                        amount=amount,
                        fulfilled=True,
                        timestamp=donation_date
                    )
                    
                    donations_created += 1
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created 5 test supporters:'))
            self.stdout.write(f'  - Sarah Johnson (@supporter_1)')
            self.stdout.write(f'  - Michael Chen (@supporter_2)')
            self.stdout.write(f'  - Emma Williams (@supporter_3)')
            self.stdout.write(f'  - James Wilson (@supporter_4)')
            self.stdout.write(f'  - Olivia Brown (@supporter_5)')
            self.stdout.write(f'  - Total donations: {donations_created}')
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {username} not found'))
        except Profile.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Profile for {username} not found'))
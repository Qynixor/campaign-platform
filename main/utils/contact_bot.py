import re

class RallynexContactBot:
    """Simple AI that answers from your FAQ"""
    
    def generate_response(self, name, message):
        name = name or "there"
        msg = message.lower()
        
        # IMPORT CONTENT FROM SOCIAL MEDIA
        if any(word in msg for word in ['import', 'tiktok', 'instagram', 'youtube', 'facebook', 'twitter', 'social media']):
            return f"""Hey {name}! Yes, you can import content from ANY platform! 🎬

Our Quick Import feature works with TikTok, Instagram, YouTube, Facebook, and X/Twitter.

**How to do it:**
1. Go to your journey's Content Manager
2. Click "Quick Import"
3. Paste the URL from any platform
4. Assign to a day or milestone

No account connections needed - just paste and go! 🔗

For personal help, email rallynex1@gmail.com 🚀"""
        
        # CREATE A JOURNEY
        elif any(word in msg for word in ['create', 'make', 'new journey', 'start journey']):
            return f"""Hey {name}! Creating a journey is easy! 🎯

**Steps:**
1. Click "Create Journey" from your Dashboard
2. Fill in title, description, and duration
3. Choose Daily Challenge or Milestone type
4. Start posting content!

You can start immediately after creation. Need more help? Email rallynex1@gmail.com ✨"""
        
        # SHARE JOURNEY
        elif any(word in msg for word in ['share', 'sharing', 'share link', 'promote']):
            return f"""Hey {name}! Sharing your journey is simple! 📢

Every journey has its own unique URL. Just copy the link from your browser's address bar and share it anywhere - social media, email, or your bio!

**If sharing isn't working:**
• Make sure you're logged in
• Check if journey is published
• Try refreshing the page

Still stuck? Email rallynex1@gmail.com with details! 🔧"""
        
        # FUNDRAISING
        elif any(word in msg for word in ['fundraising', 'donate', 'donation', 'paypal', 'raise money']):
            return f"""Hey {name}! Fundraising on Rallynex is simple! 💰

**How it works:**
1. Enable fundraising when creating/editing your journey
2. Set a goal amount and description
3. Supporters donate via PayPal
4. Funds go directly to your PayPal account

All donations are secure through PayPal. For personal help, email rallynex1@gmail.com 💝"""
        
        # FOLLOW A JOURNEY
        elif any(word in msg for word in ['follow', 'subscribe', 'track journey']):
            return f"""Hey {name}! Following a journey is easy! 🔔

Just visit any journey page and click the "Follow" button. You'll get notifications when new content is posted.

Manage all your followed journeys from your Dashboard.

Questions? Email rallynex1@gmail.com 💫"""
        
        # FREE/COST
        elif any(word in msg for word in ['free', 'cost', 'price', 'paid']):
            return f"""Hey {name}! Rallynex is COMPLETELY free! 💯

You can create and share journeys at no cost. We may add premium features later, but core features will always be free.

For any questions, email rallynex1@gmail.com 🎉"""
        
        # TECHNICAL ISSUES / NOT WORKING
        elif any(word in msg for word in ['not working', 'error', 'bug', 'broken', 'issue', 'problem']):
            return f"""Sorry you're having trouble, {name}! 😟

For technical support, please email rallynex1@gmail.com with:
• What you were trying to do
• What happened (screenshot helps!)
• Your browser and device

Our team will help you within 24 hours! 🔧"""
        
        # DEFAULT - DIRECT TO EMAIL FOR PERSONAL HELP
        else:
            return f"""Hey {name}! Thanks for reaching out! 👋

For personal help with Rallynex, please email us directly at:

📧 **rallynex1@gmail.com**

Our team will respond within 24 hours. Include as much detail as possible!

In the meantime, check our FAQ page for quick answers.

Is there anything specific I can help clarify? 🤔"""


contact_bot = RallynexContactBot()
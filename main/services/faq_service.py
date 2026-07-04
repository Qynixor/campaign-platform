# main/services/faq_service.py

import re

# Documentation-First FAQ Knowledge Base
FAQ_DATA = [
    {
        "keywords": ["journey", "what is", "documentation", "about"],
        "question": "What is a journey on Rallynex?",
        "answer": "A journey is a container for documenting progress over time. It can be a daily log (post every day) or a milestone tracker (post key achievements)."
    },
    {
        "keywords": ["create", "start", "new journey", "make"],
        "question": "How do I create a journey?",
        "answer": "Go to your Dashboard and click 'New Journey'. Fill in the title, description, duration, and choose between Daily or Milestone format. You can start adding entries immediately."
    },
    {
        "keywords": ["daily", "milestone", "difference", "type"],
        "question": "What's the difference between Daily and Milestone journeys?",
        "answer": "Daily journeys follow a calendar — each day unlocks as time passes. Milestone journeys are flexible — you document achievements whenever they happen."
    },
    {
        "keywords": ["entry", "activity", "post", "add", "content"],
        "question": "How do I add an entry to my journey?",
        "answer": "Go to your journey's Content Manager, choose a day or milestone, and click 'Add Entry'. You can write content, upload images, or add videos."
    },
    {
        "keywords": ["journal", "free-form", "write", "thoughts"],
        "question": "What is the Journal feature?",
        "answer": "The Journal is for free-form writing without being tied to a specific journey. You can write entries anytime and keep them private or share them."
    },
    {
        "keywords": ["private", "public", "unlisted", "privacy", "hide", "share"],
        "question": "How do privacy settings work?",
        "answer": "Private — Only you can see it. Unlisted — Anyone with the link can see it. Public — Everyone can discover and view it. Private is the default."
    },
    {
        "keywords": ["comment", "reply", "feedback"],
        "question": "How do comments work?",
        "answer": "If comments are enabled on a journey, you can leave comments on any entry. You can turn comments on/off in journey settings."
    },
    {
        "keywords": ["follow", "subscribe", "update", "notification"],
        "question": "How do I follow a journey?",
        "answer": "Visit any journey page and click the 'Follow' button. You'll receive notifications when new entries are posted."
    },
    {
        "keywords": ["save", "bookmark", "favorite", "later"],
        "question": "How do I save a journey?",
        "answer": "Click the 'Save' button on any journey page. Saved journeys appear in your 'Saved Journeys' section for easy access later."
    },
    {
        "keywords": ["export", "download", "backup", "pdf"],
        "question": "Can I export my journey?",
        "answer": "Yes! You can export your journey as PDF, Markdown, JSON, or HTML. Go to your journey's Export page and choose your preferred format."
    },
    {
        "keywords": ["dashboard", "home", "manage"],
        "question": "What is the Dashboard?",
        "answer": "The Dashboard is your central workspace. You can see all your journeys, recent entries, journal entries, and quick access to create new content."
    },
    {
        "keywords": ["discover", "explore", "find", "search"],
        "question": "How do I find journeys to follow?",
        "answer": "Use the Discover page to browse public journeys. You can search by title, category, or filter by type (Daily/Milestone)."
    },
    {
        "keywords": ["profile", "edit", "avatar", "bio", "photo"],
        "question": "How do I edit my profile?",
        "answer": "Go to Dashboard > Profile Settings. You can update your photo, bio, location, and social links (optional)."
    },
    {
        "keywords": ["signup", "register", "account", "create account"],
        "question": "How do I create an account?",
        "answer": "Click 'Sign up' and enter your username, email, and password. It's free and takes less than a minute. Your profile is created automatically."
    },
    {
        "keywords": ["login", "signin", "password", "reset", "forgot"],
        "question": "How do I reset my password?",
        "answer": "On the login page, click 'Forgot Password'. Enter your email and we'll send you a link to reset your password."
    },
    {
        "keywords": ["delete", "remove", "cancel"],
        "question": "Can I delete my journey?",
        "answer": "Yes. Go to your journey's Edit page and click 'Delete'. This action is permanent and cannot be undone."
    },
    {
        "keywords": ["tag", "organize", "category"],
        "question": "How do tags work?",
        "answer": "Tags help organize your journeys. Add up to 10 tags per journey (comma separated). You can filter and search by tags on the Discover page."
    }
]

def find_best_match(message):
    """Find the best matching FAQ based on user message"""
    message_lower = message.lower()
    
    best_match = None
    best_score = 0
    
    for faq in FAQ_DATA:
        score = 0
        for keyword in faq["keywords"]:
            if keyword in message_lower:
                score += 3  # Exact keyword match
            elif any(word in message_lower for word in keyword.split()):
                score += 1  # Partial match
        
        # Check word overlap
        words = message_lower.split()
        for word in words:
            if len(word) > 3:
                for keyword in faq["keywords"]:
                    if word in keyword or keyword in word:
                        score += 0.5
        
        if score > best_score:
            best_score = score
            best_match = faq
    
    return best_match if best_score >= 2 else None

def get_ai_response(message, name=""):
    """Generate AI response based on FAQ matching"""
    match = find_best_match(message)
    
    if match:
        response = f"Thanks for your question, {name}! Here's what I can tell you:\n\n"
        response += f"**{match['question']}**\n"
        response += f"{match['answer']}\n\n"
        response += f"Was this helpful? If you need more details, our team will follow up shortly."
        return response
    
    # Default response
    return f"Thanks for your question, {name}! I'm still learning, but our team will get back to you within 24 hours. In the meantime, you can check the Discover page for inspiration or explore your Dashboard.\n\n- RallyBot 🤖"
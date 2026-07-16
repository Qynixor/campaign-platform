# main/services/customization_service.py

class CustomizationService:
    """Service for handling journey customization"""
    
    # Available themes
    THEMES = {
        'default': {
            'name': 'Default',
            'primary': '#3B82F6',
            'secondary': '#6366F1',
            'background': '#FFFFFF',
            'text': '#1F2937',
            'accent': '#3B82F6',
            'font': 'Inter'
        },
        'dark': {
            'name': 'Dark Mode',
            'primary': '#8B5CF6',
            'secondary': '#6D28D9',
            'background': '#1F2937',
            'text': '#F3F4F6',
            'accent': '#8B5CF6',
            'font': 'Inter'
        },
        'vibrant': {
            'name': 'Vibrant',
            'primary': '#EF4444',
            'secondary': '#F59E0B',
            'background': '#FEF2F2',
            'text': '#1F2937',
            'accent': '#EF4444',
            'font': 'Poppins'
        },
        'pastel': {
            'name': 'Pastel',
            'primary': '#F472B6',
            'secondary': '#60A5FA',
            'background': '#FDF2F8',
            'text': '#4B5563',
            'accent': '#F472B6',
            'font': 'Quicksand'
        },
        'minimal': {
            'name': 'Minimal',
            'primary': '#000000',
            'secondary': '#6B7280',
            'background': '#FFFFFF',
            'text': '#111827',
            'accent': '#000000',
            'font': 'Inter'
        },
        'nature': {
            'name': 'Nature',
            'primary': '#10B981',
            'secondary': '#059669',
            'background': '#ECFDF5',
            'text': '#064E3B',
            'accent': '#10B981',
            'font': 'Lora'
        },
        'ocean': {
            'name': 'Ocean',
            'primary': '#0EA5E9',
            'secondary': '#0284C7',
            'background': '#F0F9FF',
            'text': '#0C4A6E',
            'accent': '#0EA5E9',
            'font': 'Inter'
        }
    }
    
    # Available fonts
    FONTS = [
        {'id': 'Inter', 'name': 'Inter', 'category': 'sans-serif'},
        {'id': 'Poppins', 'name': 'Poppins', 'category': 'sans-serif'},
        {'id': 'Quicksand', 'name': 'Quicksand', 'category': 'sans-serif'},
        {'id': 'Lora', 'name': 'Lora', 'category': 'serif'},
        {'id': 'Playfair', 'name': 'Playfair Display', 'category': 'serif'},
        {'id': 'Montserrat', 'name': 'Montserrat', 'category': 'sans-serif'},
        {'id': 'Open Sans', 'name': 'Open Sans', 'category': 'sans-serif'},
        {'id': 'Roboto', 'name': 'Roboto', 'category': 'sans-serif'},
        {'id': 'Merriweather', 'name': 'Merriweather', 'category': 'serif'},
        {'id': 'Nunito', 'name': 'Nunito', 'category': 'sans-serif'},
    ]
    
    # Available layouts
    LAYOUTS = [
        {'id': 'modern', 'name': 'Modern', 'icon': '▣'},
        {'id': 'classic', 'name': 'Classic', 'icon': '▢'},
        {'id': 'minimal', 'name': 'Minimal', 'icon': '□'},
        {'id': 'grid', 'name': 'Grid', 'icon': '⊞'},
        {'id': 'magazine', 'name': 'Magazine', 'icon': '▤'},
        {'id': 'blog', 'name': 'Blog', 'icon': '☰'},
    ]
    
    @staticmethod
    def get_user_themes(user):
        """Get all themes for a user"""
        try:
            from main.models import CustomTheme
            return CustomTheme.objects.filter(user=user).order_by('-created_at')
        except (ImportError, AttributeError):
            return []
    
    @staticmethod
    def get_active_theme(user, journey=None):
        """Get active theme for a user or journey"""
        # Check if journey has theme settings
        if journey and hasattr(journey, 'theme_settings') and journey.theme_settings:
            return journey.theme_settings
        
        # Check for CustomTheme model
        try:
            from main.models import CustomTheme
            theme = CustomTheme.objects.filter(user=user, is_active=True).first()
            if theme:
                return {
                    'name': theme.name,
                    'theme_type': theme.theme_type,
                    'primary_color': theme.primary_color,
                    'secondary_color': theme.secondary_color,
                    'background_color': theme.background_color,
                    'text_color': theme.text_color,
                    'accent_color': theme.accent_color,
                    'font_family': theme.font_family,
                    'layout_style': theme.layout_style,
                    'is_active': theme.is_active,
                    'is_default': theme.is_default
                }
        except (ImportError, AttributeError):
            pass
        
        # Return default theme
        return CustomizationService.get_default_theme()
    
    @staticmethod
    def get_default_theme():
        """Get default theme"""
        return {
            'name': 'Default',
            'theme_type': 'default',
            'primary_color': '#3B82F6',
            'secondary_color': '#6366F1',
            'background_color': '#FFFFFF',
            'text_color': '#1F2937',
            'accent_color': '#3B82F6',
            'font_family': 'Inter',
            'layout_style': 'modern',
            'is_active': True,
            'is_default': True
        }
    
    @staticmethod
    def apply_theme_to_journey(journey, theme_data):
        """Apply theme to a journey"""
        # Store theme settings in journey
        journey.theme_settings = {
            'primary_color': theme_data.get('primary_color', '#3B82F6'),
            'secondary_color': theme_data.get('secondary_color', '#6366F1'),
            'background_color': theme_data.get('background_color', '#FFFFFF'),
            'text_color': theme_data.get('text_color', '#1F2937'),
            'accent_color': theme_data.get('accent_color', '#3B82F6'),
            'font_family': theme_data.get('font_family', 'Inter'),
            'layout_style': theme_data.get('layout_style', 'modern'),
            'theme_name': theme_data.get('theme_name', 'Custom Theme'),
            'cover_image': theme_data.get('cover_image')
        }
        journey.save(update_fields=['theme_settings'])
        return journey
    
    @staticmethod
    def generate_css(journey):
        """Generate CSS for a journey's theme"""
        # Get theme settings directly from journey
        theme = getattr(journey, 'theme_settings', None)
        
        # If theme_settings is None or empty, return empty string
        if not theme or not isinstance(theme, dict):
            return ""
        
        primary = theme.get('primary_color', '#3B82F6')
        secondary = theme.get('secondary_color', '#6366F1')
        background = theme.get('background_color', '#FFFFFF')
        text = theme.get('text_color', '#1F2937')
        accent = theme.get('accent_color', '#3B82F6')
        font = theme.get('font_family', 'Inter')
        layout = theme.get('layout_style', 'modern')
        theme_name = theme.get('theme_name', 'Custom Theme')
        
        # Generate CSS
        css = f"""
        /* ===== CUSTOM THEME: {theme_name} ===== */
        @import url('https://fonts.googleapis.com/css2?family={font.replace(' ', '+')}:wght@300;400;500;600;700&display=swap');
        
        /* Override CSS variables */
        .journey-container {{
            --bg-primary: {background} !important;
            --bg-secondary: {background}dd !important;
            --bg-tertiary: {background}aa !important;
            --text-primary: {text} !important;
            --text-secondary: {text}cc !important;
            --text-muted: {text}88 !important;
            --accent: {primary} !important;
            --accent-light: {primary}22 !important;
            --accent-hover: {secondary} !important;
            --border-color: {primary}44 !important;
            --silver: {primary}66 !important;
            --silver-light: {primary}33 !important;
            --card-bg: {background} !important;
            --success: #10b981 !important;
        }}
        
        /* Force background and text */
        .journey-container {{
            background-color: {background} !important;
            color: {text} !important;
            font-family: '{font}', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        }}
        
        /* Headers */
        .journey-container h1,
        .journey-container h2,
        .journey-container h3,
        .journey-container h4,
        .journey-container .journey-title-section h1,
        .journey-container .dashboard-title,
        .journey-container .section-title {{
            color: {primary} !important;
        }}
        
        /* Buttons */
        .journey-container .btn-primary,
        .journey-container .comment-submit-btn,
        .journey-container .btn-add-reflection,
        .journey-container .btn-save,
        .journey-container .btn-submit,
        .journey-container .btn-primary-sm,
        .journey-container .btn-purchase,
        .journey-container .btn-export {{
            background-color: {primary} !important;
            border-color: {primary} !important;
            color: #ffffff !important;
        }}
        
        .journey-container .btn-primary:hover,
        .journey-container .comment-submit-btn:hover,
        .journey-container .btn-add-reflection:hover,
        .journey-container .btn-save:hover {{
            background-color: {secondary} !important;
            border-color: {secondary} !important;
        }}
        
        /* Progress bar */
        .journey-container .progress-fill {{
            background: {primary} !important;
        }}
        
        /* Links */
        .journey-container a:not(.btn):not(.btn-primary):not(.btn-secondary) {{
            color: {primary} !important;
        }}
        
        .journey-container a:not(.btn):hover {{
            color: {secondary} !important;
        }}
        
        /* Stats cards */
        .journey-container .stat-card.dashboard {{
            border-color: {primary} !important;
            background: {primary}22 !important;
        }}
        
        .journey-container .stat-card.dashboard i,
        .journey-container .stat-card.dashboard .value,
        .journey-container .stat-card.dashboard .label {{
            color: {primary} !important;
        }}
        
        .journey-container .stat-card.customize {{
            border-color: #8B5CF6 !important;
            background: #8B5CF622 !important;
        }}
        
        .journey-container .stat-card.customize i,
        .journey-container .stat-card.customize .value,
        .journey-container .stat-card.customize .label {{
            color: #8B5CF6 !important;
        }}
        
        .journey-container .stat-card:hover {{
            border-color: {primary} !important;
        }}
        
        /* Badges */
        .journey-container .badge,
        .journey-container .privacy-badge {{
            background-color: {secondary} !important;
            color: #ffffff !important;
            border-color: {secondary} !important;
        }}
        
        /* Edit link */
        .journey-container .edit-link {{
            color: {primary} !important;
        }}
        
        .journey-container .edit-link:hover {{
            color: {secondary} !important;
        }}
        
        /* Current day hero */
        .journey-container .current-day-hero {{
            border-color: {primary}44 !important;
        }}
        
        /* Hero stats border */
        .journey-container .hero-stats,
        .journey-container .goals-focus-section {{
            border-top-color: {primary}44 !important;
        }}
        
        .journey-container .journey-hero {{
            border-bottom-color: {primary}44 !important;
        }}
        
        /* Share section */
        .journey-container .share-section .share-inner {{
            border-color: {primary}44 !important;
        }}
        
        /* Info actions */
        .journey-container .info-action:hover {{
            color: {primary} !important;
        }}
        
        /* Day strip current */
        .journey-container .strip-day.current .strip-thumbnail {{
            border-color: {primary} !important;
            box-shadow: 0 0 0 2px {primary}44 !important;
        }}
        
        /* Goal progress fill */
        .journey-container .goal-card .goal-progress .progress-fill.in-progress {{
            background: {primary} !important;
        }}
        
        /* Check badge */
        .journey-container .check-badge {{
            background: {primary} !important;
        }}
        
        /* Path node */
        .journey-container .path-node.current {{
            fill: {primary} !important;
            stroke: {primary} !important;
        }}
        
        .journey-container .path-node.completed {{
            fill: #10b981 !important;
            stroke: #10b981 !important;
        }}
        
        /* Premium badge */
        .journey-container .premium-badge {{
            background: linear-gradient(135deg, {primary}, {secondary}) !important;
        }}
        """
        
        # Add layout specific styles
        css += CustomizationService._get_layout_css(layout)
        
        return css
    
    @staticmethod
    def _get_layout_css(layout):
        """Get CSS for specific layout"""
        layouts = {
            'modern': """
                .journey-container {
                    padding: 20px;
                    max-width: 800px;
                }
                .journey-hero {
                    border-radius: 16px;
                    padding: 24px;
                }
                .current-day-hero {
                    border-radius: 16px;
                }
            """,
            'classic': """
                .journey-container {
                    padding: 10px;
                    max-width: 700px;
                }
                .journey-hero {
                    border-radius: 8px;
                    padding: 20px;
                    border: 2px solid var(--theme-primary);
                }
                .current-day-hero {
                    border-radius: 8px;
                }
            """,
            'minimal': """
                .journey-container {
                    padding: 10px;
                    max-width: 650px;
                }
                .journey-hero {
                    border-radius: 0;
                    padding: 16px;
                    border-bottom: 2px solid var(--theme-primary);
                }
                .stat-card {
                    border-radius: 0;
                }
                .current-day-hero {
                    border-radius: 0;
                }
            """,
            'grid': """
                .gallery-grid {
                    grid-template-columns: repeat(4, 1fr) !important;
                }
                .journey-container {
                    max-width: 900px;
                }
            """,
            'magazine': """
                .journey-container {
                    max-width: 1000px;
                    padding: 10px;
                }
                .journey-hero {
                    padding: 30px;
                    background: linear-gradient(135deg, var(--theme-background), var(--theme-primary) + '10') !important;
                }
                .current-day-hero {
                    border-radius: 0 !important;
                }
            """,
            'blog': """
                .journey-container {
                    max-width: 700px;
                    padding: 20px;
                }
                .journey-hero {
                    padding: 20px 0;
                    border-bottom: 3px solid var(--theme-primary) !important;
                }
                .current-day-hero {
                    border-radius: 0 !important;
                    border: none !important;
                    border-bottom: 1px solid #e5e7eb !important;
                }
            """
        }
        return layouts.get(layout, layouts['modern'])
    
    @staticmethod
    def get_available_themes():
        """Get all available themes"""
        return CustomizationService.THEMES
    
    @staticmethod
    def get_available_fonts():
        """Get all available fonts"""
        return CustomizationService.FONTS
    
    @staticmethod
    def get_available_layouts():
        """Get all available layouts"""
        return CustomizationService.LAYOUTS
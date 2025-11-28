// PWA Service Worker Registration
class PWAHandler {
    constructor() {
        this.deferredPrompt = null;
        this.installPrompt = document.getElementById('pwa-install-prompt');
        this.installBtn = document.getElementById('pwa-install-btn');
        this.dismissBtn = document.getElementById('pwa-dismiss-btn');
        
        this.init();
    }

    init() {
        this.registerServiceWorker();
        this.setupInstallPrompt();
        this.detectStandaloneMode();
    }

    // Register Service Worker
    registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then(registration => {
                    console.log('RallyNex SW registered: ', registration);
                    this.checkForUpdates(registration);
                })
                .catch(error => {
                    console.log('RallyNex SW registration failed: ', error);
                });
        }
    }

    // Check for SW updates
    checkForUpdates(registration) {
        registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing;
            console.log('New service worker found...');
            
            newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                    console.log('New content available; please refresh.');
                    this.showUpdateNotification();
                }
            });
        });
    }

    // Show update notification
    showUpdateNotification() {
        // You can add a "New version available" notification here
        if (confirm('New version of RallyNex available! Reload to update?')) {
            window.location.reload();
        }
    }

    // Setup install prompt
    setupInstallPrompt() {
        if (!this.installPrompt) return;

        // Listen for beforeinstallprompt event
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            
            // Check if we should show prompt
            if (this.shouldShowPrompt()) {
                this.showInstallPrompt();
            }
        });

        // Install button click
        if (this.installBtn) {
            this.installBtn.addEventListener('click', () => {
                this.installPWA();
            });
        }

        // Dismiss button click
        if (this.dismissBtn) {
            this.dismissBtn.addEventListener('click', () => {
                this.hideInstallPrompt();
                this.setPromptDismissed();
            });
        }

        // Track app installed
        window.addEventListener('appinstalled', () => {
            console.log('RallyNex was installed successfully');
            this.hideInstallPrompt();
            this.trackInstallation();
        });
    }

    // Check if we should show install prompt
    shouldShowPrompt() {
        // Don't show if already installed
        if (this.isRunningStandalone()) return false;

        // Check if user recently dismissed
        const lastDismissed = localStorage.getItem('rallynex_pwa_dismissed');
        if (lastDismissed) {
            const daysSinceDismiss = (Date.now() - parseInt(lastDismissed)) / (1000 * 60 * 60 * 24);
            if (daysSinceDismiss < 7) return false; // Don't show for 7 days
        }

        // Check engagement (you can customize this)
        return this.hasUserEngaged();
    }

    // Check if user has engaged with the app
    hasUserEngaged() {
        // Simple engagement check - visited multiple pages or spent time
        const pageVisits = parseInt(sessionStorage.getItem('rallynex_page_visits') || '0');
        sessionStorage.setItem('rallynex_page_visits', (pageVisits + 1).toString());
        
        return pageVisits >= 2; // Show after 2 page visits
    }

    // Show install prompt
    showInstallPrompt() {
        if (this.installPrompt && this.deferredPrompt) {
            this.installPrompt.style.display = 'block';
            
            // Auto-hide after 30 seconds
            setTimeout(() => {
                this.hideInstallPrompt();
            }, 30000);
        }
    }

    // Hide install prompt
    hideInstallPrompt() {
        if (this.installPrompt) {
            this.installPrompt.style.display = 'none';
        }
    }

    // Install PWA
    async installPWA() {
        if (!this.deferredPrompt) return;

        this.deferredPrompt.prompt();
        const { outcome } = await this.deferredPrompt.userChoice;
        
        console.log(`User ${outcome} the install`);
        
        if (outcome === 'accepted') {
            this.hideInstallPrompt();
            this.trackInstallation();
        }
        
        this.deferredPrompt = null;
    }

    // Set prompt as dismissed
    setPromptDismissed() {
        localStorage.setItem('rallynex_pwa_dismissed', Date.now().toString());
    }

    // Check if running in standalone mode (already installed)
    isRunningStandalone() {
        return window.matchMedia('(display-mode: standalone)').matches || 
               window.navigator.standalone ||
               document.referrer.includes('android-app://');
    }

    // Detect standalone mode and apply styles
    detectStandaloneMode() {
        if (this.isRunningStandalone()) {
            document.documentElement.classList.add('pwa-standalone');
            console.log('RallyNex running in standalone mode');
        }
    }

    // Track installation (for analytics)
    trackInstallation() {
        // You can integrate with Google Analytics here
        console.log('PWA installation tracked');
        
        // Example: Send to analytics
        if (typeof gtag !== 'undefined') {
            gtag('event', 'pwa_installed', {
                'event_category': 'PWA',
                'event_label': 'App Installation'
            });
        }
    }
}

// Manual install trigger for your "Download" button
function showPWAInstall() {
    if (window.pwaHandler && window.pwaHandler.deferredPrompt) {
        window.pwaHandler.installPWA();
    } else {
        // Fallback: show instructions
        showInstallInstructions();
    }
}

// Show install instructions
function showInstallInstructions() {
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    const isAndroid = /Android/.test(navigator.userAgent);
    
    let message = 'To install RallyNex:\n\n';
    
    if (isIOS) {
        message += '1. Tap the Share icon (□↑)\n';
        message += '2. Select "Add to Home Screen"\n';
        message += '3. Tap "Add"';
    } else if (isAndroid) {
        message += '1. Tap the menu (⋮)\n';
        message += '2. Select "Add to Home screen"\n';
        message += '3. Tap "Add"';
    } else {
        message += 'Look for "Install" or "Add to Home Screen" in your browser menu.';
    }
    
    alert(message);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.pwaHandler = new PWAHandler();
});

// Export for global access (if needed)
window.showPWAInstall = showPWAInstall;
window.showInstallInstructions = showInstallInstructions;
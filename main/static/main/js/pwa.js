// Simple working PWA install
let deferredPrompt;

// Show install prompt when available
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    console.log('PWA install available');
});

// Working install function
function showPWAInstall() {
    if (deferredPrompt) {
        // Show native install prompt
        deferredPrompt.prompt();
        
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                console.log('User accepted install');
                // Hide your install button
                document.querySelector('.pwa-install-link').style.display = 'none';
            } else {
                console.log('User dismissed install');
            }
            deferredPrompt = null;
        });
    } else {
        // Fallback: show instructions
        showInstallInstructions();
    }
}

// Simple instructions
function showInstallInstructions() {
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    
    if (isIOS) {
        alert('To install: Tap Share → "Add to Home Screen" → "Add"');
    } else {
        alert('To install: Tap Menu (⋮) → "Add to Home screen" → "Add"');
    }
}

// Register service worker
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js')
        .then(registration => console.log('SW registered'))
        .catch(error => console.log('SW failed:', error));
}
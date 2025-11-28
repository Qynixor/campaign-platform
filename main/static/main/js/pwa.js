// Simple PWA Install Handler
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    console.log('PWA install ready');
});

function showPWAInstall() {
    if (deferredPrompt) {
        // Show the native install prompt
        deferredPrompt.prompt();
        
        deferredPrompt.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === 'accepted') {
                console.log('User installed the app');
                // Hide install button after successful install
                const installBtn = document.querySelector('.pwa-install-link');
                if (installBtn) {
                    installBtn.style.display = 'none';
                }
            }
            deferredPrompt = null;
        });
    } else {
        // Show instructions if install not available
        showInstallInstructions();
    }
}

function showInstallInstructions() {
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
    
    if (isIOS) {
        alert('To install RallyNex:\n\n1. Tap the Share icon (□↑)\n2. Select "Add to Home Screen"\n3. Tap "Add"');
    } else {
        alert('To install RallyNex:\n\n1. Tap the menu (⋮)\n2. Select "Add to Home screen"\n3. Tap "Add"');
    }
}

// Register service worker
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/main/js/sw.js')
        .then(registration => {
            console.log('Service Worker registered with scope:', registration.scope);
        })
        .catch(error => {
            console.log('Service Worker registration failed:', error);
        });
}
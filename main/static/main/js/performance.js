// Performance monitoring
(function() {
    'use strict';
    
    // Core Web Vitals
    if ('web-vitals' in window) {
        const { getCLS, getFID, getLCP } = webVitals;
        
        getCLS(console.log);
        getFID(console.log);
        getLCP(console.log);
    }
    
    // Page load time
    window.addEventListener('load', function() {
        setTimeout(function() {
            var t = performance.timing;
            var loadTime = t.loadEventEnd - t.navigationStart;
            var domReadyTime = t.domContentLoadedEventEnd - t.navigationStart;
            
            // Send to analytics
            if (window.gtag) {
                gtag('event', 'performance', {
                    'page_load_time': loadTime,
                    'dom_ready_time': domReadyTime,
                    'page': window.location.pathname
                });
            }
        }, 0);
    });
    
    // Lazy loading images
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.add('loaded');
                observer.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
    
    // Prefetch next page on hover
    const links = document.querySelectorAll('a[href]');
    const prefetchQueue = new Set();
    
    links.forEach(link => {
        link.addEventListener('mouseenter', () => {
            const url = link.href;
            if (!prefetchQueue.has(url) && url.startsWith(window.location.origin)) {
                prefetchQueue.add(url);
                const linkPrefetch = document.createElement('link');
                linkPrefetch.rel = 'prefetch';
                linkPrefetch.href = url;
                document.head.appendChild(linkPrefetch);
            }
        });
    });
})();
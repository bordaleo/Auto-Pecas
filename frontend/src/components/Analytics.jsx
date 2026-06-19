import { useEffect } from 'react';
import { useStore } from '../context/StoreContext';

function injectScript(id, src, inline) {
  if (document.getElementById(id)) return;
  const el = document.createElement('script');
  el.id = id;
  if (src) {
    el.async = true;
    el.src = src;
  } else if (inline) {
    el.innerHTML = inline;
  }
  document.head.appendChild(el);
}

export default function Analytics() {
  const { config } = useStore();
  const gaId = (config.google_analytics_id || '').trim();
  const pixelId = (config.meta_pixel_id || '').trim();

  useEffect(() => {
    if (gaId) {
      injectScript('ga-lib', `https://www.googletagmanager.com/gtag/js?id=${gaId}`);
      injectScript('ga-init', null, `
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', '${gaId}');
      `);
    }
  }, [gaId]);

  useEffect(() => {
    if (!pixelId) return;
    injectScript('meta-pixel', null, `
      !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
      n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
      n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
      t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
      document,'script','https://connect.facebook.net/en_US/fbevents.js');
      fbq('init', '${pixelId}');
      fbq('track', 'PageView');
    `);
  }, [pixelId]);

  return null;
}

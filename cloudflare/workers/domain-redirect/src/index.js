/**
 * Domain redirect worker that properly merges UTM parameters.
 * Maps vanity domains to tdrealtyohio.com with attribution tracking.
 */

const REDIRECT_MAP = {
  'sell1percentohio.com': {
    destination: 'https://tdrealtyohio.com/sell-your-home',
    utm_campaign: 'sell1percent',
  },
  '1percentlistingohio.com': {
    destination: 'https://tdrealtyohio.com/sell-your-home',
    utm_campaign: '1percentlisting',
  },
  'sellmyhousecolumbus.com': {
    destination: 'https://tdrealtyohio.com/sell-your-home',
    utm_campaign: 'sellcolumbus',
  },
  'powellohiorealestate.com': {
    destination: 'https://tdrealtyohio.com/areas/powell',
    utm_campaign: 'powell',
  },
  'dublinohiohomes.com': {
    destination: 'https://tdrealtyohio.com/areas/dublin',
    utm_campaign: 'dublin',
  },
  'firsttimebuyerohio.com': {
    destination: 'https://tdrealtyohio.com/buy',
    utm_campaign: 'firsttimebuyer',
  },
};

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const hostname = url.hostname.replace('www.', '');

    const config = REDIRECT_MAP[hostname];
    if (!config) {
      return new Response('Not found', { status: 404 });
    }

    const destUrl = new URL(config.destination);

    // Preserve original path
    if (url.pathname !== '/') {
      destUrl.pathname = destUrl.pathname + url.pathname;
    }

    // Merge parameters
    const params = new URLSearchParams(url.search);
    if (!params.has('utm_source')) params.set('utm_source', 'vanity');
    if (!params.has('utm_medium')) params.set('utm_medium', 'domain');
    if (!params.has('utm_campaign')) params.set('utm_campaign', config.utm_campaign);

    // Preserve click IDs
    ['gclid', 'msclkid', 'fbclid'].forEach(param => {
      if (url.searchParams.has(param)) {
        params.set(param, url.searchParams.get(param));
      }
    });

    destUrl.search = params.toString();

    return Response.redirect(destUrl.toString(), 301);
  },
};

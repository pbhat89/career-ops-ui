// @ts-check
/** @typedef {import('./_types.js').Provider} Provider */

// Workday provider — hits the public CXS jobs search API.
//
// Endpoint: POST https://{tenant}.{hostnum}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
//   body: {"appliedFacets":{}, "limit":N, "offset":M, "searchText":""}
//   response: {"total":N, "jobPostings":[{title, externalPath, locationsText, ...}, ...]}
//
// Auto-detects from `careers_url` matching {tenant}.wd{N}.myworkdayjobs.com/[locale/]{site},
// or explicit `workday: tenant/site` + optional `workday_host`.

const HOST_RE = /^[a-z0-9-]+\.wd\d+\.myworkdayjobs\.com$/i;
// careers_url shape: https://{tenant}.wd{N}.myworkdayjobs.com[/{locale}]/{site}
// locale prefix is optional, e.g. /ko-KR/ or /en-US/ — two letters, hyphen, two upper.
const CAREERS_RE = /^(https?:)\/\/([a-z0-9-]+)\.wd(\d+)\.myworkdayjobs\.com\/(?:[a-z]{2}-[A-Z]{2}\/)?([^/?#]+)/i;

const PAGE_LIMIT = 20;
const MAX_JOBS = 200; // hard cap so a 1000+ tenant doesn't blow up a scan

function assertWorkdayHost(hostname) {
  if (!HOST_RE.test(hostname))
    throw new Error(`workday: untrusted hostname "${hostname}" — must match *.wd<N>.myworkdayjobs.com`);
}

// Resolve {tenant, hostnum, site} from a portals entry.
// Priority: explicit workday_host + workday → URL parse of careers_url.
function resolveTenant(entry) {
  let tenant = null;
  let hostnum = null;
  let site = null;

  if (typeof entry.workday === 'string' && entry.workday.includes('/')) {
    const [t, s] = entry.workday.split('/');
    if (t && s) { tenant = t.trim(); site = s.trim(); }
  }

  if (typeof entry.workday_host === 'string') {
    const m = entry.workday_host.match(/^([a-z0-9-]+)\.wd(\d+)\.myworkdayjobs\.com$/i);
    if (m) { tenant = tenant || m[1]; hostnum = m[2]; }
  }

  if ((!tenant || !hostnum || !site) && typeof entry.careers_url === 'string') {
    const m = entry.careers_url.match(CAREERS_RE);
    if (m) {
      if (m[1].toLowerCase() !== 'https:') return null;
      tenant = tenant || m[2];
      hostnum = hostnum || m[3];
      site = site || m[4];
    }
  }

  if (!tenant || !hostnum || !site) return null;
  return { tenant, hostnum, site };
}

function buildEndpoint({ tenant, hostnum, site }) {
  return `https://${tenant}.wd${hostnum}.myworkdayjobs.com/wday/cxs/${tenant}/${site}/jobs`;
}

function buildJdOrigin({ tenant, hostnum, site }) {
  // Canonical JD URLs hang off the site path: {origin}/{site}{externalPath}
  return `https://${tenant}.wd${hostnum}.myworkdayjobs.com/${site}`;
}

/** @type {Provider} */
export default {
  id: 'workday',

  detect(entry) {
    if (entry.provider === 'workday') {
      // explicit opt-in — trust it even if fields are partial; fetch() will validate
      return { url: 'workday://' + (entry.name || 'entry') };
    }
    const resolved = resolveTenant(entry);
    if (!resolved) return null;
    try {
      const endpoint = buildEndpoint(resolved);
      assertWorkdayHost(new URL(endpoint).hostname);
      return { url: endpoint };
    } catch {
      return null;
    }
  },

  async fetch(entry, ctx) {
    const resolved = resolveTenant(entry);
    if (!resolved) throw new Error(`workday: cannot derive tenant/site for ${entry.name}`);

    const endpoint = buildEndpoint(resolved);
    const parsed = new URL(endpoint);
    if (parsed.protocol !== 'https:') throw new Error(`workday: endpoint must use HTTPS: ${endpoint}`);
    assertWorkdayHost(parsed.hostname);

    const jdOrigin = buildJdOrigin(resolved);
    const headers = { 'content-type': 'application/json', 'accept': 'application/json' };

    const jobs = [];
    const seen = new Set();
    let offset = 0;
    let total = Infinity;

    while (jobs.length < MAX_JOBS && offset < total) {
      const payload = { appliedFacets: {}, limit: PAGE_LIMIT, offset, searchText: '' };
      // redirect:'error' + hostname allowlist above guarantees the request can't
      // be steered to an attacker-controlled host via 30x.
      const json = await ctx.fetchJson(endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
        redirect: 'error',
      });

      // `total` only populates reliably on offset=0; treat it as the page-1 hint only.
      if (offset === 0 && typeof json?.total === 'number' && json.total > 0) {
        total = json.total;
      }

      const postings = Array.isArray(json?.jobPostings) ? json.jobPostings : [];
      if (postings.length === 0) break;

      for (const p of postings) {
        if (jobs.length >= MAX_JOBS) break;
        const path = typeof p?.externalPath === 'string' ? p.externalPath : '';
        if (!path || !path.startsWith('/')) continue;
        const url = jdOrigin + path;
        if (seen.has(url)) continue;
        seen.add(url);
        jobs.push({
          title: (p.title || '').trim(),
          url,
          company: entry.name,
          location: (p.locationsText || '').trim(),
        });
      }

      // If the page came back short, we've reached the end.
      if (postings.length < PAGE_LIMIT) break;
      offset += PAGE_LIMIT;
    }

    return jobs;
  },
};

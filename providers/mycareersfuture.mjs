// @ts-check
/** @typedef {import('./_types.js').Provider} Provider */

// MyCareersFuture provider — hits the public WSG search API at
// api.mycareersfuture.gov.sg. MCF is Singapore's government job board and
// almost every posting publishes a salary range (SGD, usually Monthly).
//
// Verified endpoint (probed 2026-05): GET
//   https://api.mycareersfuture.gov.sg/v2/jobs?search={kw}&limit={n}&sortBy=new_posting_date
// Returns { results: [...], total, _links }. Each job has:
//   - title
//   - postedCompany.name, hiringCompany?.name
//   - metadata.jobDetailsUrl  (canonical https://www.mycareersfuture.gov.sg/job/... URL)
//   - salary { minimum, maximum, type.salaryType }      (may be omitted when isHideSalary)
//   - address { isOverseas, districts[].region, ... }   (structured — assemble manually)
//
// Detection contract (this provider claims an entry when):
//   1. entry.provider === 'mycareersfuture', OR
//   2. entry.careers_url contains 'mycareersfuture.gov.sg', OR
//   3. entry.mcf is set — convention: a search keyword string (e.g. mcf: "Head of AI")
//
// Optional NEW field convention:
//   mcf_search: "<keyword>"        # search keyword to feed the v2 API
//   mcf_limit:  <int, default 30>  # results per call (max 100 in practice)
//   mcf_filters: { ... }           # pass-through query params (e.g. salary, postingCompany)
//
// Filtering: this provider does NOT apply title_filter / location_filter — scan.mjs
// handles those globally. We return everything the API surfaces.

const ALLOWED_MCF_HOSTS = new Set([
  'api.mycareersfuture.gov.sg',
  'www.mycareersfuture.gov.sg',
  'mycareersfuture.gov.sg',
]);

const MCF_API_BASE = 'https://api.mycareersfuture.gov.sg/v2/jobs';
const MCF_DEFAULT_LIMIT = 30;

function assertMcfUrl(url) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    throw new Error(`mycareersfuture: invalid URL: ${url}`);
  }
  if (parsed.protocol !== 'https:') throw new Error(`mycareersfuture: URL must use HTTPS: ${url}`);
  if (!ALLOWED_MCF_HOSTS.has(parsed.hostname))
    throw new Error(`mycareersfuture: untrusted hostname "${parsed.hostname}" — must be one of: ${[...ALLOWED_MCF_HOSTS].join(', ')}`);
  return url;
}

function resolveSearchKeyword(entry) {
  // Priority: explicit mcf_search > mcf shorthand > derive from careers_url ?search=
  if (typeof entry.mcf_search === 'string' && entry.mcf_search.trim()) return entry.mcf_search.trim();
  if (typeof entry.mcf === 'string' && entry.mcf.trim()) return entry.mcf.trim();
  if (typeof entry.careers_url === 'string' && entry.careers_url.includes('mycareersfuture.gov.sg')) {
    try {
      const parsed = new URL(entry.careers_url);
      const qs = parsed.searchParams.get('search');
      if (qs) return qs.trim();
    } catch { /* fall through */ }
  }
  return '';
}

function resolveApiUrl(entry) {
  const isMcfEntry =
    entry.provider === 'mycareersfuture' ||
    (typeof entry.careers_url === 'string' && entry.careers_url.includes('mycareersfuture.gov.sg')) ||
    typeof entry.mcf === 'string' ||
    typeof entry.mcf_search === 'string';
  if (!isMcfEntry) return null;

  const keyword = resolveSearchKeyword(entry);
  const limit = Number.isFinite(entry.mcf_limit) ? Math.max(1, Math.min(100, entry.mcf_limit)) : MCF_DEFAULT_LIMIT;

  const params = new URLSearchParams();
  if (keyword) params.set('search', keyword);
  params.set('limit', String(limit));
  params.set('sortBy', 'new_posting_date');

  // Pass-through filters — caller-owned, opaque to the framework.
  if (entry.mcf_filters && typeof entry.mcf_filters === 'object') {
    for (const [k, v] of Object.entries(entry.mcf_filters)) {
      if (v != null) params.set(k, String(v));
    }
  }

  return `${MCF_API_BASE}?${params.toString()}`;
}

function formatSalary(salary) {
  if (!salary || typeof salary !== 'object') return '';
  const min = Number(salary.minimum);
  const max = Number(salary.maximum);
  if (!Number.isFinite(min) && !Number.isFinite(max)) return '';
  const unit = salary?.type?.salaryType || 'Monthly';
  const fmt = (n) => `SGD ${n.toLocaleString('en-SG')}`;
  if (Number.isFinite(min) && Number.isFinite(max)) {
    if (min === max) return `${fmt(min)} ${unit}`;
    return `${fmt(min)} - ${fmt(max)} ${unit}`;
  }
  return `${fmt(Number.isFinite(min) ? min : max)} ${unit}`;
}

function formatLocation(address) {
  if (!address || typeof address !== 'object') return 'Singapore';
  if (address.isOverseas) {
    return address.overseasCountry || 'Overseas';
  }
  const districts = Array.isArray(address.districts) ? address.districts : [];
  const region = districts[0]?.region;
  const loc = districts[0]?.location;
  if (region && loc) return `Singapore — ${region} (${loc})`;
  if (region) return `Singapore — ${region}`;
  return 'Singapore';
}

function normalizeJob(raw, entry) {
  if (!raw || typeof raw !== 'object') return null;
  const title = String(raw.title || '').trim();
  const url = String(raw?.metadata?.jobDetailsUrl || '').trim();
  if (!title || !url) return null;
  // Hard-assert the canonical URL belongs to the public MCF host before emitting.
  try { assertMcfUrl(url); } catch { return null; }
  const company = String(
    raw?.hiringCompany?.name || raw?.postedCompany?.name || entry.name || '',
  ).trim();
  return {
    title,
    url,
    company,
    location: formatLocation(raw.address),
    salary: formatSalary(raw.salary),
  };
}

/** @type {Provider} */
export default {
  id: 'mycareersfuture',

  detect(entry) {
    try {
      const apiUrl = resolveApiUrl(entry);
      return apiUrl ? { url: apiUrl } : null;
    } catch {
      return null;
    }
  },

  async fetch(entry, ctx) {
    const apiUrl = resolveApiUrl(entry);
    if (!apiUrl) throw new Error(`mycareersfuture: cannot derive API URL for ${entry.name}`);
    assertMcfUrl(apiUrl);
    // redirect:'error' prevents SSRF via server-side redirects; combined with
    // assertMcfUrl above it guarantees the final hostname stays in the allowlist.
    const json = await ctx.fetchJson(apiUrl, { redirect: 'error' });
    const results = Array.isArray(json?.results) ? json.results : [];
    return results.map(r => normalizeJob(r, entry)).filter(Boolean);
  },
};

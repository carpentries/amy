/**
 * Client-side workshop metadata fetching and parsing.
 *
 * Replaces the server-side fetch_workshop_metadata / parse_workshop_metadata /
 * validate_workshop_metadata Python functions. GitHub Pages and raw GitHub
 * content both send Access-Control-Allow-Origin: *, so the browser can fetch
 * them directly without any server proxy.
 *
 * Requires js-yaml (jsyaml global) to be loaded before this script.
 */

// Mirrors Event.WEBSITE_REGEX and Event.REPO_REGEX from `src/workshops/models.py`
const WEBSITE_REGEX = /^https?:\/\/(?<name>[^.]+)\.github\.(io|com)\/(?<repo>[^/]+)\/?$/;
const REPO_REGEX = /^https?:\/\/github\.com\/(?<name>[^/]+)\/(?<repo>[^/]+)\/?$/;

const ALLOWED_METADATA_NAMES = [
    "slug", "startdate", "enddate", "country", "venue", "address",
    "latlng", "lat", "lng", "language", "eventbrite", "instructor", "helper", "contact",
];

function _workshopValidateUrl(url) {
    return WEBSITE_REGEX.test(url) || REPO_REGEX.test(url);
}

function _workshopGenerateRawUrl(url) {
    for (const regex of [WEBSITE_REGEX, REPO_REGEX]) {
        const match = regex.exec(url);
        if (match) {
            const { name, repo } = match.groups;
            return {
                rawUrl: `https://raw.githubusercontent.com/${name}/${repo}/gh-pages/index.html`,
                repo,
            };
        }
    }
    return null;
}

function _workshopParseHtmlMetadata(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const result = {};
    for (const meta of doc.querySelectorAll("meta[name]")) {
        const name = meta.getAttribute("name");
        if (ALLOWED_METADATA_NAMES.includes(name)) {
            result[name] = meta.getAttribute("content") ?? "";
        }
    }
    return result;
}

function _workshopParseYamlMetadata(text) {
    const parts = text.split("---");
    if (parts.length < 3) return {};
    let yaml;
    try {
        yaml = jsyaml.load(parts[1].trim());
    } catch (e) {
        return {};
    }
    if (!yaml || typeof yaml !== "object" || Array.isArray(yaml)) return {};
    const result = {};
    for (const key of ALLOWED_METADATA_NAMES) {
        if (!(key in yaml)) continue;
        const val = yaml[key];
        if (Array.isArray(val)) {
            result[key] = val.join("|");
        } else if (val instanceof Date) {
            const y = val.getUTCFullYear();
            const m = String(val.getUTCMonth() + 1).padStart(2, "0");
            const d = String(val.getUTCDate()).padStart(2, "0");
            result[key] = `${y}-${m}-${d}`;
        } else if (val !== null && val !== undefined) {
            result[key] = String(val);
        }
    }
    return result;
}

/**
 * Fetch raw metadata dict from a workshop URL.
 * Equivalent to Python's fetch_workshop_metadata().
 * Throws an Error if the URL is invalid or the request fails.
 */
async function fetchRawWorkshopMetadata(url) {
    if (!_workshopValidateUrl(url)) {
        throw new Error("URL must be a GitHub repository or GitHub Pages URL.");
    }

    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Request for "${url}" returned status code ${response.status}.`);
    }
    const html = await response.text();
    let metadata = _workshopParseHtmlMetadata(html);

    if (Object.keys(metadata).length === 0) {
        const raw = _workshopGenerateRawUrl(url);
        if (raw) {
            const rawResponse = await fetch(raw.rawUrl);
            if (rawResponse.ok) {
                const rawText = await rawResponse.text();
                metadata = _workshopParseYamlMetadata(rawText);
                if (!("slug" in metadata)) {
                    metadata["slug"] = raw.repo;
                }
            }
        }
    }

    return metadata;
}

/**
 * Normalise raw metadata into the structured form used to populate forms.
 * Equivalent to Python's parse_workshop_metadata().
 */
function parseWorkshopMetadata(raw) {
    const country = (raw.country || "").toUpperCase().slice(0, 2);
    const language = (raw.language || "").toUpperCase().slice(0, 2);

    let latStr, lngStr;
    if ("lat" in raw && "lng" in raw) {
        latStr = raw.lat;
        lngStr = raw.lng;
    } else {
        const parts = (raw.latlng || "").split(",");
        latStr = parts[0];
        lngStr = parts[1];
    }

    const toFloat = (s) => {
        if (s === undefined || s === null) return null;
        const v = parseFloat(String(s).trim());
        return isNaN(v) ? null : v;
    };

    const toInt = (s) => {
        if (!s) return null;
        const v = parseInt(String(s).trim(), 10);
        return isNaN(v) ? null : v;
    };

    const toDate = (s) => {
        if (!s) return null;
        return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : null;
    };

    const splitPipe = (s) => {
        if (!s) return [];
        return s.split("|").map((x) => x.trim()).filter((x) => x);
    };

    return {
        slug: raw.slug || "",
        language: language.length === 2 ? language : "",
        start: toDate(raw.startdate),
        end: toDate(raw.enddate),
        country: country.length === 2 ? country : "",
        venue: raw.venue || "",
        address: raw.address || "",
        latitude: toFloat(latStr),
        longitude: toFloat(lngStr),
        reg_key: toInt(raw.eventbrite),
        instructors: splitPipe(raw.instructor),
        helpers: splitPipe(raw.helper),
        contact: splitPipe(raw.contact),
    };
}

/**
 * Fetch and normalise metadata in one step.
 * Returns the same shape previously returned by the /workshops/events/import/ endpoint.
 */
async function fetchWorkshopMetadata(url) {
    const raw = await fetchRawWorkshopMetadata(url);
    return parseWorkshopMetadata(raw);
}

/**
 * Validate raw metadata. Equivalent to Python's validate_workshop_metadata().
 * Returns { errors: string[], warnings: string[] }.
 */
function validateWorkshopMetadata(metadata) {
    const errors = [];
    const warnings = [];

    const DATE_FMT = /^\d{4}-\d{2}-\d{2}$/;
    const SLUG_FMT = /^\d{4}-\d{2}-\d{2}-.+$/;
    const TWOCHAR_FMT = /^\w\w$/;
    const FRACTION_FMT = /^[-+]?[0-9]*\.?[0-9]*$/;
    const EVENTBRITE_FMT = /^\d+$/;
    const LATLNG_FMT = /^[-+]?[0-9]*\.?[0-9]*,\s?[-+]?[0-9]*\.?[0-9]*$/;

    const requirements = [
        { name: "slug",       display: "workshop name",      required: true,  format: SLUG_FMT },
        { name: "language",   display: null,                 required: false, format: TWOCHAR_FMT },
        { name: "startdate",  display: "start date",         required: true,  format: DATE_FMT },
        { name: "enddate",    display: "end date",           required: false, format: DATE_FMT },
        { name: "country",    display: null,                 required: true,  format: TWOCHAR_FMT },
        { name: "venue",      display: null,                 required: true,  format: null },
        { name: "address",    display: null,                 required: true,  format: null },
        { name: "instructor", display: null,                 required: true,  format: null },
        { name: "helper",     display: null,                 required: true,  format: null },
        { name: "contact",    display: null,                 required: true,  format: null },
        { name: "eventbrite", display: "Eventbrite event ID", required: false, format: EVENTBRITE_FMT },
    ];

    if ("lat" in metadata || "lng" in metadata) {
        requirements.push({ name: "lat", display: "latitude",           required: true, format: FRACTION_FMT });
        requirements.push({ name: "lng", display: "longitude",          required: true, format: FRACTION_FMT });
    } else {
        requirements.push({ name: "latlng", display: "latitude / longitude", required: true, format: LATLNG_FMT });
    }

    for (const req of requirements) {
        const displayName = req.display ? `${req.display} ${req.name}` : req.name;
        const type_ = req.required ? "required" : "optional";
        const value = metadata[req.name];

        if (value === undefined || value === null) {
            (req.required ? errors : warnings).push(`Missing ${type_} metadata ${displayName}.`);
        } else if (value === "FIXME") {
            errors.push(`Placeholder value "FIXME" for ${type_} metadata ${displayName}.`);
        } else if (req.format && (req.required || value) && !req.format.test(String(value))) {
            errors.push(
                `Invalid value "${value}" for ${type_} metadata ${displayName}: should be in format "${req.format.source}".`
            );
        }
    }

    return { errors, warnings };
}

/** JSON helpers with safe fallbacks. */
export function safeJsonParse(value, fallback) {
    if (!value)
        return fallback;
    try {
        return JSON.parse(value);
    }
    catch {
        return fallback;
    }
}
export function deepEqual(a, b) {
    if (a === b)
        return true;
    if (a instanceof Date ||
        b instanceof Date ||
        typeof a !== "object" ||
        typeof b !== "object" ||
        a === null ||
        b === null) {
        return false;
    }
    const keysA = Object.keys(a);
    const keysB = Object.keys(b);
    if (keysA.length !== keysB.length)
        return false;
    return keysA.every((key) => deepEqual(a[key], b[key]));
}

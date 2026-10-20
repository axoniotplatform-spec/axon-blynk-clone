(function () {
    'use strict';
    class ShellBridgeError extends Error {
        constructor(code, message, details = {}) {
            super(message); this.name = 'ShellBridgeError'; this.code = code; this.details = details;
        }
    }
    const callbacks = new Set(['onError', 'onSortTypeChanged', 'onDevicesUpdated', 'onValueUpdated',
        'onDeviceMetadataUpdated', 'onConnectionChanged', 'onThemeUpdated']);
    const object = value => value !== null && typeof value === 'object' && !Array.isArray(value) &&
        (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
    function json(value, seen = new Set(), depth = 0) {
        if (depth > 16) throw new ShellBridgeError('invalid_request', 'Request nesting is too deep');
        if (value === null || typeof value === 'string' || typeof value === 'boolean') return;
        if (typeof value === 'number' && Number.isFinite(value)) return;
        if ((!Array.isArray(value) && !object(value)) || seen.has(value))
            throw new ShellBridgeError('invalid_request', 'Request must contain JSON values');
        seen.add(value);
        for (const key of Reflect.ownKeys(value)) {
            if (Array.isArray(value) && key === 'length') continue;
            const descriptor = Object.getOwnPropertyDescriptor(value, key);
            if (typeof key !== 'string' || !descriptor.enumerable || !Object.hasOwn(descriptor, 'value'))
                throw new ShellBridgeError('invalid_request', 'Request must contain plain JSON properties');
            json(descriptor.value, seen, depth + 1);
        }
        seen.delete(value);
    }
    class ShellBridge {
        #pending = new Map(); #callbacks = {}; #next = 0; #destroyed = false;
        _receive(response) {
            if (this.#destroyed || !response || typeof response !== 'object') return;
            const pending = this.#pending.get(response.id);
            if (!pending) return;
            this.#pending.delete(response.id); clearTimeout(pending.timer);
            if (response.error) pending.reject(new ShellBridgeError(response.error.code,
                response.error.message, response.error.details));
            else pending.resolve(response.result);
        }
        setCallbacks(next) {
            if (!object(next)) throw new ShellBridgeError('invalid_request', 'Callbacks must be an object');
            for (const [name, callback] of Object.entries(next)) {
                if (!callbacks.has(name) || (callback !== null && typeof callback !== 'function'))
                    throw new ShellBridgeError('invalid_request', 'Invalid callback: ' + name);
            }
            Object.assign(this.#callbacks, next);
        }
        _emit(name, value) {
            if (this.#destroyed) return;
            try { Promise.resolve(this.#callbacks[name]?.(value)).catch(() => {}); } catch (_) {}
        }
        async #call(method, params = {}) {
            try {
                if (this.#destroyed) throw new ShellBridgeError('bridge_destroyed', 'Shell bridge is no longer available');
                if (typeof window.ShellNative?.request !== 'function')
                    throw new ShellBridgeError('transport_disconnected', 'Shell bridge is unavailable');
                if (this.#pending.size >= 50) throw new ShellBridgeError('too_many_requests', 'Too many pending requests');
                json(params);
                const id = String(++this.#next);
                const body = JSON.stringify({ id, method, params });
                if (body.length > 65536) throw new ShellBridgeError('invalid_request', 'Request is too large');
                return await new Promise((resolve, reject) => {
                    const timer = setTimeout(() => {
                        this.#pending.delete(id);
                        reject(new ShellBridgeError('request_timeout', 'Request timed out'));
                    }, 35000);
                    this.#pending.set(id, { resolve, reject, timer });
                    try { window.ShellNative.request(body); }
                    catch (_) {
                        this.#pending.delete(id); clearTimeout(timer);
                        reject(new ShellBridgeError('transport_disconnected', 'Connection is unavailable'));
                    }
                });
            } catch (error) { this._emit('onError', error); throw error; }
        }
        getDevices(options = {}) { return this.#call('getDevices', { options }); }
        getDevice(selector) { return this.#call('getDevice', { selector }); }
        getDeviceSegments() { return this.#call('getDeviceSegments'); }
        getDevicesSortType() { return this.#call('getDevicesSortType'); }
        getDevicesState() { return this.#call('getDevicesState'); }
        refreshDevices() { return this.#call('refreshDevices'); }
        setDeviceSegment(segmentId) { return this.#call('setDeviceSegment', { segmentId }); }
        getDeviceGroups() { return this.#call('getDeviceGroups'); }
        setDeviceGroup(groupId) { return this.#call('setDeviceGroup', { groupId }); }
        openDevice(deviceId) { return this.#call('openDevice', { deviceId }); }
        deleteDevice(deviceId) { return this.#call('deleteDevice', { deviceId }); }
        openAddDevice() { return this.#call('openAddDevice'); }
        getDeviceDashboard(deviceId) { return this.#call('getDeviceDashboard', { deviceId }); }
        executeDataEngineQuery(options) { return this.#call('executeDataEngineQuery', { options }); }
        showPage(deviceId, pageIndex) { return this.#call('showPage', { deviceId, pageIndex }); }
        getHistoryData(options) { return this.#call('getHistoryData', { options }); }
        getHistoricalData(options) { return this.getHistoryData(options); }
        getMapData(options) { return this.#call('getMapData', { options }); }
        getTimeline(options) { return this.#call('getTimeline', { options }); }
        getTimelinePermissions(deviceId) { return this.#call('timeline', { deviceId, request: { operation: 'permissions' } }); }
        getTimelineComments(deviceId, id) { return this.#timeline(deviceId, { operation: 'comments', id }); }
        addTimelineComment(deviceId, id, comment) { return this.#timeline(deviceId, { operation: 'comment', id, comment }); }
        resolveTimelineEvent(deviceId, id, comment) {
            return this.#timeline(deviceId, { operation: 'resolve', id, ...(comment === undefined ? {} : { comment }) });
        }
        archiveTimelineEvent(deviceId, id) { return this.#timeline(deviceId, { operation: 'archive', id }); }
        unarchiveTimelineEvent(deviceId, id) { return this.#timeline(deviceId, { operation: 'unarchive', id }); }
        createTimelineNote(deviceId, note) { return this.#timeline(deviceId, { operation: 'note', ...note }); }
        #timeline(deviceId, request) { return this.#call('timeline', { deviceId, request }); }
        sendValue(deviceId, stream, value) { return this.#call('sendValue', { deviceId, stream, value }); }
        getAllDeviceMetadata(deviceId, options = {}) {
            return this.#call('metadata', { deviceId, request: { operation: 'list', options } });
        }
        getDeviceMetadata(deviceId, selector, options = {}) {
            return this.#call('metadata', { deviceId, request: { operation: 'get', selector, options } });
        }
        updateDeviceMetadata(deviceId, selector, valuePatch) {
            return this.#call('metadata', { deviceId, request: { operation: 'update', selector, valuePatch } });
        }
        isPermissionAllowed(permission, deviceId) {
            return this.#call('isPermissionAllowed', { permission, ...(deviceId === undefined ? {} : { deviceId }) });
        }
        getTheme() { return this.#call('getTheme'); }
        destroy() {
            if (this.#destroyed) return;
            this.#destroyed = true;
            for (const p of this.#pending.values()) {
                clearTimeout(p.timer); p.reject(new ShellBridgeError('bridge_destroyed', 'Shell bridge is no longer available'));
            }
            this.#pending.clear(); this.#callbacks = {};
        }
    }
    window.ShellBridgeError = ShellBridgeError;
    window.shellBridge = new ShellBridge();
    window.addEventListener('pagehide', () => window.shellBridge.destroy(), { once: true });
})();

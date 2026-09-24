/**
 *	ui_module_data.js
 *
 *	Copyright 2015 Roland Corporation. All rights reserved.
 */

/**
 *	@class module snapshot.
 *	@constructor
 */
function UIModuleSnapshot(slot) {
	this.slot = slot;
	this.params = [];
	this.connections = {
		in: [],
		out: [],
	};
}

/**
 *	@class module data.
 */
function UIModuleData() {}

UIModuleData.SEND_MIDI = 1;
UIModuleData.SEND_AUDIO = 2;

UIModuleData.MAIN_PARAM_COUNT = 10;
UIModuleData.MAIN_IN_COUNT = 10;
UIModuleData.MAIN_OUT_COUNT = 10;

UIModuleData.SUB_PARAM_COUNT = 4;
UIModuleData.SUB_IN_COUNT = 4;
UIModuleData.SUB_OUT_COUNT = 2;

UIModuleData.UNTITLED_FILE_NAME = 'Untitled';
UIModuleData.PATCH_FILE_EXTENSION = 'bin';
UIModuleData.AUDIO_FILE_EXTENSION = 'wav';


UIModuleData.PARAM_COUNT = function(slot) {
	return (slot > 0) ? this.SUB_PARAM_COUNT : this.MAIN_PARAM_COUNT;
}

UIModuleData.INPUT_COUNT = function(slot) {
	return (slot > 0) ? this.SUB_IN_COUNT : this.MAIN_IN_COUNT;
}

UIModuleData.OUTPUT_COUNT = function(slot) {
	return (slot > 0) ? this.SUB_OUT_COUNT : this.MAIN_OUT_COUNT;
}

UIModuleData._cableColorIndex = 1;

UIModuleData.nextCableColorIndex = function() {
	this._cableColorIndex++;
	if (this._cableColorIndex >= UIModuleConfigs.cableColors.length) {
		this._cableColorIndex = 1;
	}
	return this._cableColorIndex;
}

UIModuleData.sendType = function() {
	return (globals.system.isMobile || globals.pref.transfer_audio) ? this.SEND_AUDIO : this.SEND_MIDI;
}

UIModuleData.modified = function(modified) {
	if (modified != null) {
		globals.patch.setModified(modified);
	}
	return globals.patch.getModified();
}


UIModuleData.initialize = function() {
	var type = globals.pref.main_module;
	if (type == null || type < UIModuleConfigs.MIN_MAIN_TYPE || type > UIModuleConfigs.MAX_MAIN_TYPE) {
		return false;
	}
	globals.patch.setValue(0, 0, type);
	this.load(UIModuleConfigs.initialPatchPath(type), true);
	globals.patch.setPatchName(UIModuleData.UNTITLED_FILE_NAME);
	return true;
}

UIModuleData.reset = function(type, unsend) {
	if (type == null) {
		type = this.moduleType(0);
	}
	if (type < UIModuleConfigs.MIN_MAIN_TYPE || type > UIModuleConfigs.MAX_MAIN_TYPE) {
		return;
	}
	if (type != this.moduleType(0)) {
		globals.patch.setValue(0, 0, type);
	}
	if (type != globals.pref.main_module) {
		globals.pref.main_module = type;
		globals.app.saveState();
	}
	this.load(UIModuleConfigs.initialPatchPath(type), unsend);
	globals.patch.setPatchName(UIModuleData.UNTITLED_FILE_NAME);
}

UIModuleData.resetSlot = function(slot, type, disconnect) {
	var configs = (slot > 0) ? UIModuleConfigs.sub[type] : UIModuleConfigs.main[type];
	var params = configs.params;

	globals.undoManager.storeModule(slot);

	if (slot == 0 && type != globals.pref.main_module) {
		globals.pref.main_module = type;
		globals.app.saveState();
	}

	globals.patch.setValue(slot, 0, type);
	for (var i = 1; i <= this.PARAM_COUNT(slot); i++) {
		if (params[i] != null) {
			globals.patch.setValue(slot, i, params[i].init);
		} else {
			globals.patch.setValue(slot, i, 0);
		}
	}

	if (disconnect) {
		this.disconnectAll(slot);
	}
	globals.patch.setModified(true);
	this.sendParameters(slot);
}

UIModuleData.load = function(path, unsend) {
	if (!path || path.length <= 0) {
		return false;
	}
	var pfio = new PatchFileIO();
	if (!pfio.LoadPatchFile(globals.patch, path)) {
		return false;
	}
	if (globals.pref.main_module != this.moduleType(0)) {
		globals.pref.main_module = this.moduleType(0);
		globals.app.saveState();
	}
	globals.patch.setModified(false);
	if (!unsend) {
		this.sendPatchSafely();
	}
	return true;
}

UIModuleData.save = function(path, resetModified) {
	if (!path || path.length <= 0) {
		return false;
	}
	var pfio = new PatchFileIO();
	if (!pfio.SavePatchFile(globals.patch, path)) {
		return false;
	}
	if (resetModified) {
		globals.patch.setModified(false);
	}
	return true;
}

UIModuleData.import = function(path, unsend) {
	if (!path || path.length <= 0) {
		return false;
	}
	var succeed = LoadPatchWaveFile(globals.patch, path);
	// - 読み込みが失敗しても patch が部分的に変更されている可能性がある.
	// - 読み込みの成否によらず patch の状態を反映する.
	if (globals.pref.main_module != this.moduleType(0)) {
		globals.pref.main_module = this.moduleType(0);
		globals.app.saveState();
	}
	globals.patch.setModified(false);
	if (succeed && !unsend) {
		this.sendPatchSafely();
	}
	return succeed;
}

UIModuleData.export = function(path) {
	if (!path || path.length <= 0) {
		return false;
	}
	return SavePatchWaveFile(globals.patch, path);
}

UIModuleData.moduleType = function(slot) {
	return globals.patch.getValue(slot, 0);
}

UIModuleData.parameter = function(slot, index) {
	return globals.patch.getValue(slot, index)
}

UIModuleData.setParameter = function(slot, index, value, tracking, unsend) {
	if (unsend) {
		globals.patch.setValue(slot, index, value);
		globals.patch.setModified(true);
	} else {
		globals.uiEventController.ModifyKnobControlParameter(slot, index, value, !tracking, this.sendType());
	}
}

UIModuleData.connectedColor = function(jack1, jack2) {
	var co, ci;
	if (jack2.type == 'output') {
		co = GetOutConnectorIndex(jack2.slot, jack2.index);
		ci = GetInConnectorIndex(jack1.slot, jack1.index);
	} else {
		co = GetOutConnectorIndex(jack1.slot, jack1.index);
		ci = GetInConnectorIndex(jack2.slot, jack2.index);
	}
	return globals.patch.getConnection(co, ci);
}

UIModuleData.connect = function(jack1, jack2, color, unsend) {
	var co, ci;
	if (jack2.type == 'output') {
		co = GetOutConnectorIndex(jack2.slot, jack2.index);
		ci = GetInConnectorIndex(jack1.slot, jack1.index);
	} else {
		co = GetOutConnectorIndex(jack1.slot, jack1.index);
		ci = GetInConnectorIndex(jack2.slot, jack2.index);
	}
	if (unsend) {
		globals.patch.setConnection(co, ci, color);
		globals.patch.setModified(true);
	} else {
		globals.uiEventController.ModifyConnectControlParameter(co, ci, color, true, this.sendType());
	}
	return globals.patch.getConnection(co, ci);
}

UIModuleData.disconnect = function(jack1, jack2, unsend) {
	this.connect(jack1, jack2, 0, unsend);
}

UIModuleData.disconnectAll = function(slot, unsend) {

	function disconnect(slot) {
		for (var i = 0; i < UIModuleData.INPUT_COUNT(slot); i++) {
			var ci = GetInConnectorIndex(slot, i);
			for (var s = 0; s <= UIModuleConfigs.MAX_SUB_SLOT; s++) {
				for (var o = 0; o < UIModuleData.OUTPUT_COUNT(s); o++) {
					var co = GetOutConnectorIndex(s, o);
					globals.patch.setConnection(co, ci, 0);
				}
			}
		}
		for (var o = 0; o < UIModuleData.OUTPUT_COUNT(slot); o++) {
			var co = GetOutConnectorIndex(slot, o);
			for (var s = 0; s <= UIModuleConfigs.MAX_SUB_SLOT; s++) {
				for (var i = 0; i < UIModuleData.INPUT_COUNT(s); i++) {
					var ci = GetInConnectorIndex(s, i);
					globals.patch.setConnection(co, ci, 0);
				}
			}
		}
	}

	if (slot != null) {
		disconnect(slot);
	}
	else {
		for (var s = 0; s <= UIModuleConfigs.MAX_SUB_SLOT; s++) {
			disconnect(s);
		}
	}

	globals.patch.setModified(true);
	if (!unsend) {
		this.sendConnections();
	}
}

UIModuleData.sendAll = function() {
	this.sendPatchSafely();
}

// SYSTEM-1 oscillator port (2026-09-22): a SYSTEM oscillator uses as much DSP time as two or three stock
// modules, and the unit removes old modules with a delay. Sending a whole patch at once can briefly run
// the outgoing and incoming oscillators together, which overloads the DSP and hangs the unit.
// So: clear cables, empty all six slots, wait, then send the patch (tested: 30/30 preset switches).
UIModuleData.SWITCH_GAP_MS = 600;

UIModuleData.sendEmptySubModules = function() {
	var zeros = [];
	for (var i = 0; i < 30; i++) {
		zeros.push(0);
	}
	globals.uiEventController.eventQueue.enqueue(new UIEvent(globals.patch.getModelId(),
		0x10, 0x10, 0x00, 0x00, zeros, true, this.sendType()));
}

UIModuleData.sendPatchSafely = function() {
	this.sendClearConnections(); // noise 対策.
	this.sendEmptySubModules();
	var self = this;
	setTimeout(function() {
		self.sendParameters();
		self.sendConnections();
	}, this.SWITCH_GAP_MS);
}

UIModuleData.sendParameters = function(/* slot1 , slot2, ... */) {
	var sendType = this.sendType();
	var count = arguments.length;
	if (count <= 0) {
		globals.uiEventController.ModifyAllMainModuleParameter(sendType);
		globals.uiEventController.ModifyAllSubModuleParameter(sendType);
		return;
	}
	var main = false;
	var sub = false;
	for (var i = 0; i < count; i++) {
		var arg = arguments[i];
		if (arg instanceof Array) {
			var c = arg.length;
			for (var j = 0; j < c; j++) {
				if (arg[j] > 0) {
					sub = true;
				} else {
					main = true;
				}
				if (main && sub) {
					break;
				}
			}
		} else {
			if (arg > 0) {
				sub = true;
			} else {
				main = true;
			}
		}
		if (main && sub) {
			break;
		}
	}
	if (main) {
		globals.uiEventController.ModifyAllMainModuleParameter(sendType);
	}
	if (sub) {
		globals.uiEventController.ModifyAllSubModuleParameter(sendType);
	}
}

UIModuleData.sendConnections = function() {
	globals.uiEventController.ModifyAllConnectionParameter(this.sendType());
}

UIModuleData.sendClearConnections = function(slots) {
	globals.uiEventController.ClearAllConnectionParameter(slots, this.sendType());
}

UIModuleData.snapshot = function(slot) {
	var snapshot = new UIModuleSnapshot(slot);

	// parameters.
	for (var i = 0; i <= this.PARAM_COUNT(slot); i++) {
		snapshot.params[i] = this.parameter(slot, i);
	}
	// input connections.
	for (var i = 0; i < this.INPUT_COUNT(slot); i++) {
		var ci = GetInConnectorIndex(slot, i);
		snapshot.connections.in[i] = [];
		for (var s = 0; s <= UIModuleConfigs.MAX_SUB_SLOT; s++) {
			for (var o = 0; o < this.OUTPUT_COUNT(s); o++) {
				var co = GetOutConnectorIndex(s, o);
				snapshot.connections.in[i][co] = globals.patch.getConnection(co, ci);
			}
		}
	}
	// output connections.
	for (var o = 0; o < this.OUTPUT_COUNT(slot); o++) {
		var co = GetOutConnectorIndex(slot, o);
		snapshot.connections.out[o] = [];
		for (var s = 0; s <= UIModuleConfigs.MAX_SUB_SLOT; s++) {
			for (var i = 0; i < this.INPUT_COUNT(s); i++) {
				var ci = GetInConnectorIndex(s, i);
				snapshot.connections.out[o][ci] = globals.patch.getConnection(co, ci);
			}
		}
	}
	return snapshot;
}

UIModuleData.snapshots = function(slot1 /*, slot2, ... */) {
	var snapshots = [];
	if (slot1 != null) {
		var count = arguments.length();
		for (var i = 0; i < count; i++) {
			snapshots[i] = this.snapshot(arguments[i]);
		}
	}
	else {
		for (var i = 0; i <= UIModuleConfigs.MAX_SUB_SLOT; i++) {
			snapshots[i] = this.snapshot(i);
		}
	}
	return snapshots;
}

UIModuleData.restore = function(snapshot, send) {

	function restore1(snapshot) {
		if (snapshot == null) {
			return false;
		}
		var slot = snapshot.slot;

		if (slot == 0 && snapshot.params[0] != globals.pref.main_module) {
			globals.pref.main_module = snapshot.params[0];
			globals.app.saveState();
		}

		// parameters.
		for (var i = 0; i <= UIModuleData.PARAM_COUNT(slot); i++) {
			globals.patch.setValue(slot, i, snapshot.params[i]);
		}
		// input connections.
		for (var i = 0; i < UIModuleData.INPUT_COUNT(slot); i++) {
			var ci = GetInConnectorIndex(slot, i);
			for (var s = 0; s <= UIModuleConfigs.MAX_SUB_SLOT; s++) {
				for (var o = 0; o < UIModuleData.OUTPUT_COUNT(s); o++) {
					var co = GetOutConnectorIndex(s, o);
					globals.patch.setConnection(co, ci, snapshot.connections.in[i][co]);
				}
			}
		}
		// output connections.
		for (var o = 0; o < UIModuleData.OUTPUT_COUNT(slot); o++) {
			var co = GetOutConnectorIndex(slot, o);
			for (var s = 0; s <= UIModuleConfigs.MAX_SUB_SLOT; s++) {
				for (var i = 0; i < UIModuleData.INPUT_COUNT(s); i++) {
					var ci = GetInConnectorIndex(s, i);
					globals.patch.setConnection(co, ci, snapshot.connections.out[o][ci]);
				}
			}
		}
		globals.patch.setModified(true);
		return true;
	}

	if (snapshot instanceof Array) {
		var slots = [];
		var count = snapshot.length;
		for (var i = 0; i < count; i++) {
			restore1(snapshot[i]);
			slots.push(snapshot[i].slot);
		}
		if (send && slots.length > 0) {
			this.sendClearConnections(slots); // noise 対策.
			this.sendParameters(slots);
			this.sendConnections();
		}
	}
	else {
		restore1(snapshot);
		if (send) {
			this.sendClearConnections([ snapshot.slot ]); // noise 対策.
			this.sendParameters(snapshot.slot);
			this.sendConnections();
		}
	}
}

UIModuleData.exchangeSubModules = function(slot1, slot2, send, undoable) {
	if (slot1 <= 0 || slot2 <= 0) {
		return false;
	}
	if (slot1 == slot2) {
		return false;
	}
	if (undoable) {
		globals.undoManager.storeModule(slot1, slot2);
	}

	var snapshot1 = this.snapshot(slot1);
	var snapshot2 = this.snapshot(slot2);

	// parameters.
	for (var i = 0; i <= this.SUB_PARAM_COUNT; i++) {
		globals.patch.setValue(slot1, i, snapshot2.params[i]);
		globals.patch.setValue(slot2, i, snapshot1.params[i]);
	}
	// external input connections.
	for (var i = 0; i < this.SUB_IN_COUNT; i++) {
		var ci1 = GetInConnectorIndex(slot1, i);
		var ci2 = GetInConnectorIndex(slot2, i);
		for (var s = 0; s <= UIModuleConfigs.MAX_SUB_SLOT; s++) {
			if (s == slot1 || s == slot2) {
				continue;
			}
			for (var o = 0; o < this.OUTPUT_COUNT(s); o++) {
				var co = GetOutConnectorIndex(s, o);
				globals.patch.setConnection(co, ci1, snapshot2.connections.in[i][co]);
				globals.patch.setConnection(co, ci2, snapshot1.connections.in[i][co]);
			}
		}
	}
	// external output connections.
	for (var o = 0; o < this.SUB_OUT_COUNT; o++) {
		var co1 = GetOutConnectorIndex(slot1, o);
		var co2 = GetOutConnectorIndex(slot2, o);
		for (var s = 0; s <= UIModuleConfigs.MAX_SUB_SLOT; s++) {
			if (s == slot1 || s == slot2) {
				continue;
			}
			for (var i = 0; i < this.INPUT_COUNT(s); i++) {
				var ci = GetInConnectorIndex(s, i);
				globals.patch.setConnection(co1, ci, snapshot2.connections.out[o][ci]);
				globals.patch.setConnection(co2, ci, snapshot1.connections.out[o][ci]);
			}
		}
	}
	// internal connections.
	for (var i = 0; i < this.SUB_IN_COUNT; i++) {
		var ci1 = GetInConnectorIndex(slot1, i);
		var ci2 = GetInConnectorIndex(slot2, i);
		for (var o = 0; o < this.SUB_OUT_COUNT; o++) {
			var co1 = GetOutConnectorIndex(slot1, o);
			var co2 = GetOutConnectorIndex(slot2, o);
			globals.patch.setConnection(co1, ci1, snapshot2.connections.in[i][co2]);
			globals.patch.setConnection(co2, ci1, snapshot2.connections.in[i][co1]);
			globals.patch.setConnection(co1, ci2, snapshot1.connections.in[i][co2]);
			globals.patch.setConnection(co2, ci2, snapshot1.connections.in[i][co1]);
		}
	}
	globals.patch.setModified(true);

	if (send) {
		this.sendClearConnections([ slot1, slot2 ]); // noise 対策.
		this.sendParameters(slot1, slot2);
		this.sendConnections();
	}
	return true;
}

UIModuleData.storeSnapshot = function() {
	var name = globals.patch.getPatchName();
	if (!name || name.length <= 0) {
		name = this.UNTITLED_FILE_NAME;
	}
	globals.pref.snapshot = {
		'name': (name != null) ? name : UIModuleData.UNTITLED_FILE_NAME,
		'modified': globals.patch.getModified(),
	};

	var path = globals.fileop.dir('cache');
	if (path && path[path.length - 1] !== '/') {
		path += '/';
	}
	path += 'cache';
	globals.fileop.mkdir(path);
	path += '/snapshot.' + this.PATCH_FILE_EXTENSION;

	this.save(path, false);
	globals.patch.setPatchName(globals.pref.snapshot.name);
}

UIModuleData.restoreSnapshot = function() {
	var snapshot = globals.pref.snapshot;
	if (!snapshot) {
		return false;
	}

	var path = globals.fileop.dir('cache');
	if (path && path[path.length - 1] !== '/') {
		path += '/';
	}
	path += 'cache/snapshot.' + this.PATCH_FILE_EXTENSION;

	var stat = globals.fileop.stat(path);
	if (!stat.success) {
		globals.pref.snapshot = null;
		return false;
	}

	this.load(path);
	globals.patch.setPatchName(snapshot.name);
	globals.patch.setModified(snapshot.modified);

	if (globals.pref.main_module != this.moduleType(0)) {
		globals.pref.main_module = this.moduleType(0);
		globals.app.saveState();
	}

	globals.fileop.unlink(path);
	globals.pref.snapshot = null;
	return true;
}

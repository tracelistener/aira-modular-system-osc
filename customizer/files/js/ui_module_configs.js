/**
 *	ui_module_configs.js
 *
 *	Copyright 2015 Roland Corporation. All rights reserved.
 */

function UIModuleConfigs() {}

UIModuleConfigs.CANVAS_SIZE = UISize.make(1536, 2048);
UIModuleConfigs.PATCH_NAME_FRAME = UIRect.make(388, 22, 760, 48);

UIModuleConfigs.MIN_MAIN_TYPE = 1;
UIModuleConfigs.MAX_MAIN_TYPE = 4;

UIModuleConfigs.MIN_SUB_TYPE = 1;
UIModuleConfigs.MAX_SUB_TYPE = 31;

UIModuleConfigs.MIN_SUB_SLOT = 1;
UIModuleConfigs.MAX_SUB_SLOT = 6;

/**
 *	cable colors.
 */
UIModuleConfigs.cableColors = [
	'#000000', // dummy.
	'#cc0000',
	'#00cccc',
	'#cc4400',
	'#0088cc',
	'#cc8800',
	'#0044cc',
	'#cccc00',
	'#0000cc',
	'#88cc00',
	'#4400cc',
	'#44cc00',
	'#8800cc',
	'#00cc00',
	'#cc00cc',
	'#00cc44',
	'#cc0088',
	'#00cc88',
	'#cc0044',
];

/**
 *	slots.
 */
 UIModuleConfigs.slot = [
	{ // main slot.
		frame: UIRect.make(386, 966, 764, 874),
		row: 1,
		column: 1,
	},
	{ // sub slot 1.
		frame: UIRect.make(4, 92, 382, 874),
		row: 0,
		column: 0,
	},
	{ // sub slot 2.
		frame: UIRect.make(386, 92, 382, 874),
		row: 0,
		column: 1,
	},
	{ // sub slot 3.
		frame: UIRect.make(768, 92, 382, 874),
		row: 0,
		column: 2,
	},
	{ // sub slot 4.
		frame: UIRect.make(1150, 92, 382, 874),
		row: 0,
		column: 3,
	},
	{ // sub slot 5.
		frame: UIRect.make(4, 966, 382, 874),
		row: 1,
		column: 0,
	},
	{ // sub slot 6.
		frame: UIRect.make(1150, 966, 382, 874),
		row: 1,
		column: 3,
	},
 ];

/**
 *	base views.
 */
UIModuleConfigs.views = {
	'button.sqr': {
		type: 'button',
		image: 'btn_sqr',
		size: UISize.make(46, 53),
		states: {
			tracking: UIPoint.make(1, 1),
			selected: UIPoint.make(1, 1),
		}
	},
	'knob.s': {
		type: 'knob',
		image: 'knob_s',
		size: UISize.make(88, 88),
		tooltip: true,
	},
	'knob.l': {
		type: 'knob',
		image: 'knob_l',
		size: UISize.make(130, 130),
		tooltip: true,
	},
	'jack.in': {
		type: 'jack_in',
		size: UISize.make(68, 68),
	},
	'jack.out': {
		type: 'jack_out',
		size: UISize.make(68, 68),
	},
};

/**
 *	base layouts.
 */
UIModuleConfigs.layouts = {
	// main.
	'main': [
		// buttons.
		{ // sw1.
			base: 'button.sqr',
			position: UIPoint.make(90, 238),
			param: 1,
		},
		{ // sw2.
			base: 'button.sqr',
			position: UIPoint.make(628, 238),
			param: 2,
		},
		// knobs.
		{ // prm1.
			base: 'knob.l',
			position: UIPoint.make(216, 110),
			param: 3,
		},
		{ // prm2.
			base: 'knob.l',
			position: UIPoint.make(418, 110),
			param: 4,
		},
		{ // prm3.
			base: 'knob.l',
			position: UIPoint.make(216, 654),
			param: 5,
		},
		{ // prm4.
			base: 'knob.l',
			position: UIPoint.make(418, 654),
			param: 6,
		},
		{ // level1.
			base: 'knob.s',
			position: UIPoint.make(238, 328),
			param: 7,
		},
		{ // level2.
			base: 'knob.s',
			position: UIPoint.make(440, 328),
			param: 8,
		},
		{ // level3.
			base: 'knob.s',
			position: UIPoint.make(238, 468),
			param: 9,
		},
		{ // level4.
			base: 'knob.s',
			position: UIPoint.make(440, 468),
			param: 10,
		},
		// input jacks.
		{ // audio out1.
			base: 'jack.in',
			position: UIPoint.make(1239-386, 1881-966),
			input: 0,
		},
		{ // audio out2.
			base: 'jack.in',
			position: UIPoint.make(1375-386, 1881-966),
			input: 1,
		},
		{ // efx in1.
			base: 'jack.in',
			position: UIPoint.make(78, 700),
			input: 2,
		},
		{ // efx in2.
			base: 'jack.in',
			position: UIPoint.make(78, 780),
			input: 3,
		},
		{ // efx sw1.
			base: 'jack.in',
			position: UIPoint.make(78, 72),
			input: 4,
		},
		{ // efx sw2.
			base: 'jack.in',
			position: UIPoint.make(618, 72),
			input: 5,
		},
		{ // efx knob1.
			base: 'jack.in',
			position: UIPoint.make(78, 338),
			input: 6,
		},
		{ // efx knob2.
			base: 'jack.in',
			position: UIPoint.make(618, 338),
			input: 7,
		},
		{ // efx knob3.
			base: 'jack.in',
			position: UIPoint.make(78, 478),
			input: 8,
		},
		{ // efx knob4.
			base: 'jack.in',
			position: UIPoint.make(618, 478),
			input: 9,
		},
		// output jacks.
		{ // audio in1.
			base: 'jack.out',
			position: UIPoint.make(93-386, 1881-966),
			output: 0,
		},
		{ // audio in2.
			base: 'jack.out',
			position: UIPoint.make(229-386, 1881-966),
			output: 1,
		},
		{ // knob1.
			base: 'jack.out',
			position: UIPoint.make(394-386, 1881-966),
			output: 2,
		},
		{ // knob2.
			base: 'jack.out',
			position: UIPoint.make(530-386, 1881-966),
			output: 3,
		},
		{ // knob3.
			base: 'jack.out',
			position: UIPoint.make(666-386, 1881-966),
			output: 4,
		},
		{ // knob4.
			base: 'jack.out',
			position: UIPoint.make(802-386, 1881-966),
			output: 5,
		},
		{ // sw1.
			base: 'jack.out',
			position: UIPoint.make(938-386, 1881-966),
			output: 6,
		},
		{ // sw2.
			base: 'jack.out',
			position: UIPoint.make(1074-386, 1881-966),
			output: 7,
		},
		{ // efx out1.
			base: 'jack.out',
			position: UIPoint.make(618, 700),
			output: 8,
		},
		{ // efx out2.
			base: 'jack.out',
			position: UIPoint.make(618, 780),
			output: 9,
		},
	],
};

/**
 *	base tooltips.
 */
UIModuleConfigs.tooltips = {
	'sw': ['OFF','ON'],
	'pf2': ['LPF','HPF'],
	'pf3': ['LPF','BPF','HPF'],
	'muldiv': ['4','3','8/3','2','3/2','4/3','1','3/4','2/3','1/2','3/8','1/3','1/4'],
	'formant': ['a','i','u','e','o'],
	'sign': ['+','-'],

	'wave': function (min, max, value) {
		var w1, w2;
		switch (Math.floor((value - min) / 20)) {
			case 0:
				w1 = 'SAW';
				w2 = 'TRI';
				break;
			case 1:
				w1 = 'TRI';
				w2 = 'SIN';
				break;
			case 2:
				w1 = 'SIN';
				w2 = 'SQR';
				break;
			case 3:
				w1 = 'SQR';
				w2 = 'RND';
				break;
			case 4:
				w1 = 'RND';
				w2 = 'NOISE';
				break;
			case 5:
				return 'NOISE';
			default:
				return '';
		}
		var p = (value - min) % 20;
		if (p == 0) {
			return w1;
		}
		return w1 + ' ' + (20 - p) + ':' + p + ' ' + w2;
	},

	'pan': function(min, max, value) {
		var center = Math.floor((min + max) / 2);
		if (value > center) {
			return '+' + (value - center);
		}
		if (value < center) {
			return '-' + (center - value);
		}
		return '0';
	},

	'crossFade': function(min, max, value) {
		return 'IN1 ' + (max - value) + ' : IN2 ' + value;
	},

	'plus1': function(min, max, value) {
		return '' + (value + 1);
	},
};

/**
 *	main modules.
 */
UIModuleConfigs.main = {
	/**
	 *	BYPASS.
	 */
	0: {
		name: "BYPASS",
		type: 0,
		params: {},
		layout: [],
	},
	/**
	 *	BITRAZER.
	 */
	1: {
		name: "BITRAZER",
		type: 1,
		params: {
			 1: { index: 1, min:  0, max:  1, init:  0, tooltip:UIModuleConfigs.tooltips['pf2'], },
			 2: { index: 2, min:  0, max:  1, init:  0, tooltip:UIModuleConfigs.tooltips['sw'], },
			 3: { index: 3, min:  0, max:100, init:  0, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init:  0, tooltip:true, },
			 5: { index: 5, min:  0, max:100, init: 50, tooltip:true, },
			 6: { index: 6, min:  0, max:100, init:  0, tooltip:true, },
			 7: { index: 7, min:  0, max:100, init:100, tooltip:true, },
			 8: { index: 8, min:  0, max:100, init:100, tooltip:true, },
			 9: { index: 9, min:  0, max:100, init: 50, tooltip:true, },
			10: { index:10, min:  0, max:100, init:100, tooltip:true, },
		},
		layout: [
			UIModuleConfigs.layouts['main'],
		],
	},
	/**
	 *	DEMORA.
	 */
	2: {
		name: "DEMORA",
		type: 2,
		params: {
			 1: { index: 1, min:  0, max:  1, init:  0, tooltip:UIModuleConfigs.tooltips['sw'], },
			 2: { index: 2, min:  0, max:  1, init:  0, tooltip:UIModuleConfigs.tooltips['sw'], },
			 3: { index: 3, min:  0, max:100, init:  0, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init:  0, tooltip:true, },
			 5: { index: 5, min:  0, max:100, init:  0, tooltip:true, },
			 6: { index: 6, min:  0, max:100, init:  0, tooltip:true, },
			 7: { index: 7, min:  0, max:100, init: 10, tooltip:true, },
			 8: { index: 8, min:  0, max:100, init:100, tooltip:true, },
			 9: { index: 9, min:  0, max:100, init:100, tooltip:true, },
			10: { index:10, min:  0, max:100, init:100, tooltip:true, },
		},
		layout: [
			UIModuleConfigs.layouts['main'],
		],
	},
	/**
	 *	TORCIDO.
	 */
	3: {
		name: "TORCIDO",
		type: 3,
		params: {
			 1: { index: 1, min:  0, max:  1, init:  0, tooltip:UIModuleConfigs.tooltips['sw'], },
			 2: { index: 2, min:  0, max:  1, init:  0, tooltip:UIModuleConfigs.tooltips['sw'], },
			 3: { index: 3, min:  0, max:100, init:  0, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init:  0, tooltip:true, },
			 5: { index: 5, min:  0, max:100, init:  0, tooltip:true, },
			 6: { index: 6, min:  0, max:100, init:  0, tooltip:true, },
			 7: { index: 7, min:  0, max:100, init:100, tooltip:true, },
			 8: { index: 8, min:  0, max:100, init:100, tooltip:true, },
			 9: { index: 9, min:  0, max:100, init:100, tooltip:true, },
			10: { index:10, min:  0, max:100, init:100, tooltip:true, },
		},
		layout: [
			UIModuleConfigs.layouts['main'],
		],
	},
	/**
	 *	SCOOPER.
	 */
	4: {
		name: "SCOOPER",
		type: 4,
		params: {
			 1: { index: 1, min:  0, max:  1, init:  0, tooltip:UIModuleConfigs.tooltips['sw'], },
			 2: { index: 2, min:  0, max:  1, init:  0, tooltip:UIModuleConfigs.tooltips['sw'], },
			 3: { index: 3, min:  0, max:  9, init:  0, tooltip:UIModuleConfigs.tooltips['plus1'], },
			 4: { index: 4, min:  0, max:  9, init:  0, tooltip:UIModuleConfigs.tooltips['plus1'], },
			 5: { index: 5, min:  0, max:100, init:  0, tooltip:UIModuleConfigs.tooltips['pan'], },
			 6: { index: 6, min:  0, max:100, init:  0, tooltip:UIModuleConfigs.tooltips['pan'], },
			 7: { index: 7, min:  0, max:100, init:100, tooltip:true, },
			 8: { index: 8, min:  0, max:100, init:100, tooltip:true, },
			 9: { index: 9, min:  0, max:100, init:100, tooltip:true, },
			10: { index:10, min:  0, max:100, init:100, tooltip:true, },
		},
		layout: [
			UIModuleConfigs.layouts['main'],
		],
	}
};

/**
 *	sub modules.
 */
UIModuleConfigs.sub = {
	/**
	 *	EMPTY.
	 */
	0: {
		name: "EMPTY",
		type: 0,
		params: {},
		layout: [],
	},
	/**
	 *	LFO.
	 */
	1: {
		name: "LFO",
		type: 1,
		params: {
			 1: { index: 1, min:  0, max:100, init:  0, tooltip:UIModuleConfigs.tooltips['wave'], },
			 2: { index: 2, min:  0, max:100, init: 50, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init:100, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init: 50, tooltip:true, },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(182, 108),
				param: 1,
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(182, 314),
				param: 2,
			},
			{ // prm3.
				base: 'knob.s',
				position: UIPoint.make(52, 236),
				param: 3,
			},
			{ // prm4.
				base: 'knob.s',
				position: UIPoint.make(91, 730),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(62, 391),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(62, 527),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(62, 73),
				input: 2,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(213, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(213, 780),
				output: 1,
			},
		],
	},
	/**
	 *	ADSR.
	 */
	2: {
		name: "ADSR",
		type: 2,
		params: {
			 1: { index: 1, min:  0, max:100, init:  0, tooltip:true, },
			 2: { index: 2, min:  0, max:100, init:100, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init:100, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init:  0, tooltip:true, },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(184, 108),
				param: 1,
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(68, 268),
				param: 2,
			},
			{ // prm3.
				base: 'knob.l',
				position: UIPoint.make(184, 426),
				param: 3,
			},
			{ // prm4.
				base: 'knob.l',
				position: UIPoint.make(68, 586),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(98, 780),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(52, 73),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(262, 267),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(52, 421),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(216, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(216, 780),
				output: 1,
			},
		],
	},
	/**
	 *	NOISE.
	 */
	3: {
		name: "NOISE",
		type: 3,
		params: {
			 1: { index: 1, min:  0, max:100, init:  0, tooltip:true, },
			 2: { index: 2, min:  0, max:100, init:  0, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init: 50, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init: 50, tooltip:true, },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(182, 108),
				param: 1,
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(182, 518),
				param: 2,
			},
			{ // prm3.
				base: 'knob.s',
				position: UIPoint.make(56, 320),
				param: 3,
			},
			{ // prm4.
				base: 'knob.s',
				position: UIPoint.make(56, 730),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(64, 73),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(64, 483),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(64, 187),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(64, 597),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(212, 330),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(212, 740),
				output: 1,
			},
		],
	},
	/**
	 *	SAMPLE & HOLD.
	 */
	4: {
		name: "SMPLHLD",
		type: 4,
		params: {
			 1: { index: 1, min:  0, max:100, init: 50, tooltip:true, },
			 2: { index: 2, min:  0, max:100, init:100, tooltip:true, },
			 3: { index: 3, min:  0, max:  1, init:  0, tooltip:['RATE','TRIG IN'], },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(180, 192),
				param: 1,
			},
			{ // prm2.
				base: 'knob.s',
				position: UIPoint.make(56, 116),
				param: 2,
			},
			{ // prm3.
				base: 'button.sqr',
				position: UIPoint.make(262, 440),
				param: 3,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(102, 700),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(102, 780),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(66, 273),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(66, 353),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(210, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(210, 780),
				output: 1,
			},
		],
	},
	/**
	 *	RING MOD.
	 */
	5: {
		name: "RINGMOD",
		type: 5,
		params: {
			 1: { index: 1, min:  0, max:  1, init:  1, tooltip:UIModuleConfigs.tooltips['sw'], },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'button.sqr',
				position: UIPoint.make(166, 150),
				param: 1,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(94, 362),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(218, 362),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(156, 256),
				input: 2,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(157, 700),
				output: 0,
			},
		],
	},
	/**
	 *	FILTER 6dB.
	 */
	6: {
		name: "FILTER6",
		type: 6,
		params: {
			 1: { index: 1, min:  0, max:  2, init:  0, tooltip:UIModuleConfigs.tooltips['pf3'], },
			 2: { index: 2, min:  0, max:100, init:100, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init:100, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init:  0, tooltip:true, },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.s',
				position: UIPoint.make(202, 116),
				param: 1,
				options: {
					xClips: [6,13,19],
					trackMetrics: 60,
				},
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(182, 282),
				param: 2,
			},
			{ // prm3.
				base: 'knob.s',
				position: UIPoint.make(52, 206),
				param: 3,
			},
			{ // prm4.
				base: 'knob.l',
				position: UIPoint.make(182, 486),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(101, 700),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(101, 780),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(62, 363),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(62, 444),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(213, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(213, 780),
				output: 1,
			},
		],
	},
	/**
	 *	FILTER 12dB.
	 */
	7: {
		name: "FILTER12",
		type: 7,
		params: {
			 1: { index: 1, min:  0, max:  2, init:  0, tooltip:UIModuleConfigs.tooltips['pf3'], },
			 2: { index: 2, min:  0, max:100, init:100, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init:100, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init:  0, tooltip:true, },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.s',
				position: UIPoint.make(202, 116),
				param: 1,
				options: {
					xClips: [6,13,19],
					trackMetrics: 60,
				},
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(182, 282),
				param: 2,
			},
			{ // prm3.
				base: 'knob.s',
				position: UIPoint.make(52, 206),
				param: 3,
			},
			{ // prm4.
				base: 'knob.l',
				position: UIPoint.make(182, 486),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(101, 700),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(101, 780),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(62, 363),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(62, 444),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(213, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(213, 780),
				output: 1,
			},
		],
	},
	/**
	 *	TONE.
	 */
	8: {
		name: "TONE",
		type: 8,
		params: {
			 1: { index: 1, min:  0, max:  2, init:  0, tooltip:['LOW','MID','HIGH'], },
			 2: { index: 2, min:  0, max:100, init: 50, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init: 50, tooltip:UIModuleConfigs.tooltips['pan'], },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.s',
				position: UIPoint.make(202, 116),
				param: 1,
				options: {
					xClips: [6,13,19],
					trackMetrics: 60,
				},
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(182, 290),
				param: 2,
			},
			{ // prm3.
				base: 'knob.l',
				position: UIPoint.make(182, 492),
				param: 3,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(96, 700),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(96, 780),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(62, 247),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(62, 448),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(218, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(218, 780),
				output: 1,
			},
		],
	},
	/**
	 *	AMP.
	 */
	9: {
		name: "AMP",
		type: 9,
		params: {
			 1: { index: 1, min:  0, max:100, init: 0, tooltip:true, },
			 2: { index: 2, min:  0, max:100, init: 0, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init:50, tooltip:UIModuleConfigs.tooltips['pan'], },
			 4: { index: 4, min:  0, max:100, init:50, tooltip:UIModuleConfigs.tooltips['pan'], },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(180, 134),
				param: 1,
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(180, 548),
				param: 2,
			},
			{ // prm3.
				base: 'knob.s',
				position: UIPoint.make(56, 218),
				param: 3,
			},
			{ // prm4.
				base: 'knob.s',
				position: UIPoint.make(56, 632),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(102, 368),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(102, 780),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(66, 72),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(66, 486),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(212, 368),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(212, 780),
				output: 1,
			},
		],
	},
	/**
	 *	MIXER.
	 */
	10: {
		name: "MIXER",
		type: 10,
		params: {
			 1: { index: 1, min:  0, max:100, init:100, tooltip:true, },
			 2: { index: 2, min:  0, max:100, init:100, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init:100, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init:100, tooltip:true, },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.s',
				position: UIPoint.make(222, 112),
				param: 1,
			},
			{ // prm2.
				base: 'knob.s',
				position: UIPoint.make(222, 258),
				param: 2,
			},
			{ // prm3.
				base: 'knob.s',
				position: UIPoint.make(222, 404),
				param: 3,
			},
			{ // prm4.
				base: 'knob.s',
				position: UIPoint.make(222, 550),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(82, 122),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(82, 268),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(82, 414),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(82, 560),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(232, 740),
				output: 0,
			},
		],
	},
	/**
	 *	STEREO MIXER.
	 */
	11: {
		name: "SMIXER",
		type: 11,
		params: {
			 1: { index: 1, min:  0, max:100, init:100, tooltip:true, },
			 2: { index: 2, min:  0, max:100, init:100, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init: 50, tooltip:UIModuleConfigs.tooltips['pan'], },
			 4: { index: 4, min:  0, max:100, init: 50, tooltip:UIModuleConfigs.tooltips['pan'], },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(188, 108),
				param: 1,
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(188, 438),
				param: 2,
			},
			{ // prm3.
				base: 'knob.s',
				position: UIPoint.make(146, 280),
				param: 3,
			},
			{ // prm4.
				base: 'knob.s',
				position: UIPoint.make(146, 610),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(66, 98),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(66, 180),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(66, 428),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(66, 510),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(116, 780),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(198, 780),
				output: 1,
			},
		],
	},
	/**
	 *	CURVE CONV.
	 */
	12: {
		name: "CRVCON",
		type: 12,
		params: {
			 1: { index: 1, min:  0, max:  6, init:  0, tooltip:['A1','A2','B','C1','C2','Sin1','Sin2'], },
			 2: { index: 2, min:  0, max:  1, init:  0, tooltip:UIModuleConfigs.tooltips['sw'], },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(127, 154),
				param: 1,
				options: {
					xClips: [16,21,27,32,37,43,48],
					trackMetrics: 200,
				},
			},
			{ // prm2.
				base: 'button.sqr',
				position: UIPoint.make(264, 360),
				param: 2,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(96, 700),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(96, 780),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(52, 348),
				input: 2,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(218, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(218, 780),
				output: 1,
			},
		],
	},
	/**
	 *	GATE DIVIDER.
	 */
	13: {
		name: "GATEDIV",
		type: 13,
		params: {
			 1: { index: 1, min:  0, max: 12, init:  6, tooltip:UIModuleConfigs.tooltips['muldiv'], },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(128, 256),
				param: 1,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(96, 780),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(74, 116),
				input: 1,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(218, 780),
				output: 0,
			},
		],
	},
	/**
	 *	TRIG TO DELAY TIME CV.
	 */
	14: {
		name: "TRIG_DTIME",
		type: 14,
		params: {
			 1: { index: 1, min:  0, max: 12, init:  6, tooltip:UIModuleConfigs.tooltips['muldiv'], },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(126, 294),
				param: 1,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(96, 700),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(56, 122),
				input: 1,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(218, 700),
				output: 0,
			},
		],
	},
	/**
	 *	MIDI CLOCK TO GATE.
	 */
	15: {
		name: "MIDICVG",
		type: 15,
		params: {
			 1: { index: 1, min:  0, max: 12, init:  6, tooltip:UIModuleConfigs.tooltips['muldiv'], },
			 2: { index: 2, min:  0, max:  1, init:  0, tooltip:UIModuleConfigs.tooltips['sign'], },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(126, 330),
				param: 1,
			},
			{ // prm2.
				base: 'button.sqr',
				position: UIPoint.make(168, 548),
				param: 2,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(62, 182),
				input: 0,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(218, 780),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(96, 780),
				output: 1,
			},
		],
	},
	/**
	 *	SHORT DELAY.
	 */
	16: {
		name: "SHORT_D",
		type: 16,
		params: {
			 1: { index: 1, min:  0, max:100, init: 50, tooltip:true, },
			 2: { index: 2, min:  0, max:100, init:  0, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init: 50, tooltip:true, },
		},
		layout: [
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(180, 108),
				param: 1,
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(180, 312),
				param: 2,
			},
			{ // prm3.
				base: 'knob.l',
				position: UIPoint.make(180, 514),
				param: 3,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(102, 740),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(62, 72),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(62, 276),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(62, 478),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(212, 740),
				output: 0,
			},
		],
	},
	/**
	 *	TUBE CLIP.
	 */
	17: {
		name: "TUBEC",
		type: 17,
		params: {
			 1: { index: 1, min:  0, max:100, init:  0, tooltip:true, },
			 2: { index: 2, min:  0, max:100, init:100, tooltip:true, },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(178, 210),
				param: 1,
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(178, 447),
				param: 2,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(102, 700),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(102, 780),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(62, 122),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(62, 360),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(211, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(211, 780),
				output: 1,
			},
		],
	},
	/**
	 *	COMPRESSOR.
	 */
	18: {
		name: "COMP",
		type: 18,
		params: {
			 1: { index: 1, min:  0, max:100, init:  0, tooltip:true, },
			 2: { index: 2, min:  0, max:100, init:  0, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init: 10, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init: 10, tooltip:true, },
		},
		layout: [
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(186, 108),
				param: 1,
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(64, 244),
				param: 2,
			},
			{ // prm3.
				base: 'knob.l',
				position: UIPoint.make(186, 380),
				param: 3,
			},
			{ // prm4.
				base: 'knob.l',
				position: UIPoint.make(64, 516),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(96, 700),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(96, 780),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(76, 72),
				input: 2,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(218, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(218, 780),
				output: 1,
			},
		],
	},
	/**
	 *	NOISE GATE.
	 */
	19: {
		name: "NOISG",
		type: 19,
		params: {
			 1: { index: 1, min:  0, max:100, init:100, tooltip:true, },
			 2: { index: 2, min:  0, max:100, init:  0, tooltip:true, },
		},
		layout: [
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(182, 210),
				param: 1,
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(182, 448),
				param: 2,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(100, 700),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(100, 780),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(62, 122),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(62, 360),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(212, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(212, 780),
				output: 1,
			},
		],
	},
	/**
	 *	3BAND EQ.
	 */
	20: {
		name: "3EQ",
		type: 20,
		params: {
			 1: { index: 1, min:  0, max:100, init: 50, tooltip:UIModuleConfigs.tooltips['pan'], },
			 2: { index: 2, min:  0, max:100, init: 50, tooltip:UIModuleConfigs.tooltips['pan'], },
			 3: { index: 3, min:  0, max:100, init: 50, tooltip:UIModuleConfigs.tooltips['pan'], },
		},
		layout: [
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(180, 108),
				param: 1,
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(180, 312),
				param: 2,
			},
			{ // prm3.
				base: 'knob.l',
				position: UIPoint.make(180, 514),
				param: 3,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(102, 740),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(62, 72),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(62, 276),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(62, 478),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(212, 740),
				output: 0,
			},
		],
	},
	/**
	 *	LOGIC OPERATION.
	 */
	21: {
		name: "LOGIOPE",
		type: 21,
		params: {
			 1: { index: 1, min:  0, max:100, init:100, tooltip:true, },
			 2: { index: 2, min:  0, max:100, init:100, tooltip:true, },
			 3: { index: 3, min:  0, max:  7, init:  0, tooltip:UIModuleConfigs.tooltips['plus1'], },
			 4: { index: 4, min:  0, max:100, init:100, tooltip:true, },
		},
		layout: [
			{ // prm1.
				base: 'knob.s',
				position: UIPoint.make(56, 284),
				param: 1,
			},
			{ // prm2.
				base: 'knob.s',
				position: UIPoint.make(238, 284),
				param: 2,
			},
			{ // prm3.
				base: 'knob.l',
				position: UIPoint.make(126, 110),
				param: 3,
				options: {
					xClips: [16,21,27,32,37,43,48,53],
					trackMetrics: 200,
				},
			},
			{ // prm4.
				base: 'knob.s',
				position: UIPoint.make(56, 622),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(66, 428),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(248, 428),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(156, 374),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(66, 780),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(248, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(248, 780),
				output: 1,
			},
		],
	},
	/**
	 *	CROSS FADE.
	 */
	22: {
		name: "CROSF",
		type: 22,
		params: {
			 1: { index: 1, min:  0, max:100, init:  0, tooltip:UIModuleConfigs.tooltips['crossFade'], },
			 2: { index: 2, min:  0, max:  2, init:  0, tooltip:['Transition','Constatnt Power','Intermediate'], },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(126, 380),
				param: 1,
			},
			{ // prm2.
				base: 'knob.s',
				position: UIPoint.make(202, 116),
				param: 2,
				options: {
					xClips: [6,13,19],
					trackMetrics: 60,
				},
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(56, 576),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(258, 576),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(56, 274),
				input: 2,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(156, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(156, 780),
				output: 1,
			},
		],
	},
	/**
	 *	SWITCHER.
	 */
	23: {
		name: "SWITCH",
		type: 23,
		params: {
			 1: { index: 1, min:  0, max:  1, init:  0, tooltip:['IN 1','IN 2'], },
			 2: { index: 2, min:  0, max:  1, init:  0, tooltip:['LATCH','MOMENTARY'], },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'button.sqr',
				position: UIPoint.make(168, 382),
				param: 1,
			},
			{ // prm2.
				base: 'knob.s',
				position: UIPoint.make(148, 116),
				param: 2,
				options: {
					xClips: [13,19],
					trackMetrics: 60,
					inverse: true,
				},
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(52, 486),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(52, 700),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(52, 244),
				input: 2,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(258, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(258, 486),
				output: 1,
			},
		],
	},
	/**
	 *	ENVELOPER.
	 */
	24: {
		name: "ENVE",
		type: 24,
		params: {
			 1: { index: 1, min:  0, max:100, init:  0, tooltip:true, },
			 2: { index: 2, min:  0, max:100, init:  0, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init:100, tooltip:true, },
		},
		layout: [
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(180, 108),
				param: 1,
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(180, 312),
				param: 2,
			},
			{ // prm3.
				base: 'knob.l',
				position: UIPoint.make(180, 514),
				param: 3,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(102, 740),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(62, 72),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(62, 276),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(62, 478),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(212, 700),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(212, 780),
				output: 1,
			},
		],
	},
	/**
	 *	TRIG TO LFO RATE CV.
	 */
	25: {
		name: "TRI_RATE",
		type: 25,
		params: {
			 1: { index: 1, min:  0, max: 12, init:  6, tooltip:UIModuleConfigs.tooltips['muldiv'], },
		},
		layout: [
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(126, 294),
				param: 1,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(96, 700),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(56, 122),
				input: 1,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(218, 700),
				output: 0,
			},
		],
	},
	/**
	 *	FILTER 18dB.
	 */
	26: {
		name: "FILTER18",
		type: 26,
		params: {
			 1: { index: 1, min:  0, max:  2, init:  0, tooltip:UIModuleConfigs.tooltips['pf3'], },
			 2: { index: 2, min:  0, max:100, init:100, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init:100, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init:  0, tooltip:true, },
		},
		layout: [
			{ // prm1.
				base: 'knob.s',
				position: UIPoint.make(202, 116),
				param: 1,
				options: {
					xClips: [6,13,19],
					trackMetrics: 60,
				},
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(182, 282),
				param: 2,
			},
			{ // prm3.
				base: 'knob.s',
				position: UIPoint.make(52, 206),
				param: 3,
			},
			{ // prm4.
				base: 'knob.l',
				position: UIPoint.make(182, 486),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(101, 740),
				input: 0,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(62, 363),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(62, 444),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(213, 740),
				output: 0,
			},
		],
	},
	/**
	 *	FILTER 24dB.
	 */
	27: {
		name: "FILTER24",
		type: 27,
		params: {
			 1: { index: 1, min:  0, max:  2, init:  0, tooltip:UIModuleConfigs.tooltips['pf3'], },
			 2: { index: 2, min:  0, max:100, init:100, tooltip:true, },
			 3: { index: 3, min:  0, max:100, init:100, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init:  0, tooltip:true, },
		},
		layout: [
			{ // prm1.
				base: 'knob.s',
				position: UIPoint.make(202, 116),
				param: 1,
				options: {
					xClips: [6,13,19],
					trackMetrics: 60,
				},
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(182, 282),
				param: 2,
			},
			{ // prm3.
				base: 'knob.s',
				position: UIPoint.make(52, 206),
				param: 3,
			},
			{ // prm4.
				base: 'knob.l',
				position: UIPoint.make(182, 486),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(101, 740),
				input: 0,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(62, 363),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(62, 444),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(213, 740),
				output: 0,
			},
		],
	},
	/**
	 *	SYSTEM OSCILLATOR (replaces FORMANT FILTER; needs the SYSTEM OSCILLATOR SCOOPER firmware).
	 *	P1 RANGE 1..5 = 64' 32' 16' 8' 4'. P2 WAVE 0..6 = FM, FM+SYNC, TRI, LOGIC, NOISE SAW, VOWEL, CB. P3 COLOR. P4 unused.
	 *	In: CV IN, FINE IN (1.0 = 1.2 semitones, as the stock SAW/SQR), COLOR IN (added to COLOR, clamped),
	 *	SYNC TRIG IN (rising edge through 0.3 restarts the wave; strikes CB, which is silent without it).
	 */
	28: {
		name: "OSCTRI",
		type: 28,
		params: {
			 1: { index: 1, min:  1, max:  5, init:  2, tooltip:['128','64','32','16','8','4'], },
			 2: { index: 2, min:  0, max:  6, init:  0, tooltip:['FM','FM+SYNC','TRI','LOGIC','NOISE SAW','VOWEL','CB'], },
			 3: { index: 3, min:  0, max:100, init:  0, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init:100, tooltip:true, },
		},
		layout: [
			{ // prm1: RANGE.
				base: 'knob.l',
				position: UIPoint.make(202, 88),
				param: 1,
				options: {
					xClips: [16,21,27,32,37],
					trackMetrics: 200,
				},
			},
			{ // prm2: WAVE (SYSTEM selector firmware).
				base: 'knob.l',
				position: UIPoint.make(202, 268),
				param: 2,
				options: { xClips: [16,21,27,32,37,43,48], trackMetrics: 200 },
			},
			{ // prm3: COLOR.
				base: 'knob.l',
				position: UIPoint.make(48, 268),
				param: 3,
			},
			// input jacks.
			{ // in1: CV IN (pitch).
				base: 'jack.in',
				position: UIPoint.make(79, 740),
				input: 0,
			},
			{ // in2: FINE IN (1.0 = 1.2 semitones, as the stock SAW/SQR).
				base: 'jack.in',
				position: UIPoint.make(234, 456),
				input: 1,
			},
			{ // in3: COLOR IN (added to COLOR, clamped, as the stock SAW/SQR).
				base: 'jack.in',
				position: UIPoint.make(79, 456),
				input: 2,
			},
			{ // in4: SYNC TRIG IN (rising edge through 0.3 hard-syncs the wave; strikes CB).
				base: 'jack.in',
				position: UIPoint.make(79, 597),
				input: 3,
			},
			// output jacks.
			{ // out1: OUT.
				base: 'jack.out',
				position: UIPoint.make(234, 740),
				output: 0,
			},
			{ // out2: SYNC OUT (SYSTEM saw; hard-syncs native oscillators, verified over USB).
				base: 'jack.out',
				position: UIPoint.make(234, 597),
				output: 1,
			},
		],
	},
	/**
	 *	SAW OSCILLATOR.
	 */
	29: {
		name: "OSCSAW",
		type: 29,
		params: {
			 1: { index: 1, min:  0, max:  5, init:  1, tooltip:['64','32','16','8','4','2'], },
			 2: { index: 2, min:  0, max:100, init: 50, tooltip:UIModuleConfigs.tooltips['pan'], },
			 3: { index: 3, min:  0, max:100, init:  0, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init: 50, tooltip:true, },
		},
		layout: [
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(202, 88),
				param: 1,
				options: {
					xClips: [16,21,27,32,37,43],
					trackMetrics: 200,
				},
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(202, 268),
				param: 2,
			},
			{ // prm3.
				base: 'knob.l',
				position: UIPoint.make(48, 268),
				param: 3,
			},
			{ // prm4.
				base: 'knob.s',
				position: UIPoint.make(68, 586),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(79, 740),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(234, 456),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(79, 456),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(79, 119),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(234, 740),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(234, 597),
				output: 1,
			},
		],
	},
	/**
	 *	SQR OSCILLATOR.
	 */
	30: {
		name: "OSCSQR",
		type: 30,
		params: {
			 1: { index: 1, min:  0, max:  5, init:  1, tooltip:['64','32','16','8','4','2'], },
			 2: { index: 2, min:  0, max:100, init: 50, tooltip:UIModuleConfigs.tooltips['pan'], },
			 3: { index: 3, min:  0, max:100, init:  0, tooltip:true, },
			 4: { index: 4, min:  0, max:100, init: 50, tooltip:true, },
		},
		layout: [
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(202, 88),
				param: 1,
				options: {
					xClips: [16,21,27,32,37,43],
					trackMetrics: 200,
				},
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(202, 268),
				param: 2,
			},
			{ // prm3.
				base: 'knob.l',
				position: UIPoint.make(48, 268),
				param: 3,
			},
			{ // prm4.
				base: 'knob.s',
				position: UIPoint.make(68, 586),
				param: 4,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(79, 740),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(234, 456),
				input: 1,
			},
			{ // in3.
				base: 'jack.in',
				position: UIPoint.make(79, 456),
				input: 2,
			},
			{ // in4.
				base: 'jack.in',
				position: UIPoint.make(79, 119),
				input: 3,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(234, 740),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(234, 597),
				output: 1,
			},
		],
	},
	/**
	 *	MIDI NOTE TO CV/GATE.
	 */
	31: {
		name: "MIDINOTE",
		type: 31,
		params: {
			 1: { index: 1, min:  0, max:  6, init:  3, tooltip:UIModuleConfigs.tooltips['pan'], },
			 2: { index: 2, min:  0, max: 24, init: 12, tooltip:UIModuleConfigs.tooltips['pan'], },
			 3: { index: 3, min:  0, max:  1, init:  0, tooltip:UIModuleConfigs.tooltips['sign'], },
		},
		layout: [
			// knobs.
			{ // prm1.
				base: 'knob.l',
				position: UIPoint.make(174, 240),
				param: 1,
				options: {
					xClips: [16,21,27,32,37,43,48],
					trackMetrics: 200,
				},
			},
			{ // prm2.
				base: 'knob.l',
				position: UIPoint.make(174, 456),
				param: 2,
			},
			{ // prm3.
				base: 'button.sqr',
				position: UIPoint.make(72, 520),
				param: 3,
			},
			// input jacks.
			{ // in1.
				base: 'jack.in',
				position: UIPoint.make(62, 182),
				input: 0,
			},
			{ // in2.
				base: 'jack.in',
				position: UIPoint.make(62, 370),
				input: 1,
			},
			// output jacks.
			{ // out1.
				base: 'jack.out',
				position: UIPoint.make(98, 780),
				output: 0,
			},
			{ // out2.
				base: 'jack.out',
				position: UIPoint.make(218, 780),
				output: 1,
			},
		],
	},
};

/**
 *	utilities.
 */
UIModuleConfigs.tooltip = function(param, value) {
	if (param.tooltip instanceof Array) {
		return param.tooltip[value];
	}
	if (param.tooltip instanceof Function) {
		return param.tooltip(param.min, param.max, value);
	}
	return '' + value;
}

UIModuleConfigs.initialPatchPath = function(type) {
	if (type == null) {
		type = 1;
	}
	var comps = decodeURI(location.pathname).split('/');
	comps.pop();

	if (globals.system.isIE()) {
		if (comps[0].length <= 0) {
			// IE は local filepath の場合でも先頭に '/' が付加される.
			var letter = /^[A-Za-z]:$/;
			if (letter.test(comps[1])) {
				comps.shift();
			}
		}
	}

	var path = comps.join('/') + '/bin/' + UIModuleConfigs.main[type].name + '_Initial.bin';
	// globals.log('initial patch: ' + path);
	return path;
}

UIModuleConfigs.mainBackgroundImageName = function(type) {
	return 'PNL_' + UIModuleConfigs.main[type].name + '.png';
}

UIModuleConfigs.subBackgroundImageName = function(type, row) {
	return 'PNL_' + UIModuleConfigs.sub[type].name + '.png';
}

UIModuleConfigs.randomCableColorIndex = function() {
	return Math.floor(Math.random() * (UIModuleConfigs.cableColors.length - 1)) + 1;
}

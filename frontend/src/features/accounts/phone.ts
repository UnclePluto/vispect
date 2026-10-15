export function normalizePhone(raw:unknown){if(typeof raw!=='string')return null;const phone=raw.replace(/[\s-]/g,'').replace(/^(?:\+86|0086)/,'');return /^1[3-9]\d{9}$/.test(phone)?'+86'+phone:null}

import '@testing-library/jest-dom/vitest';
import {transferableAbortController} from 'node:util';
// Node 的 fetch 与 jsdom 的取消信号属于不同运行环境，测试统一使用 Node 原生实现。
const nativeController=transferableAbortController();
globalThis.AbortController=nativeController.constructor as typeof AbortController;
globalThis.AbortSignal=nativeController.signal.constructor as typeof AbortSignal;
Object.defineProperty(window,'matchMedia',{writable:true,value:(query:string)=>({matches:false,media:query,onchange:null,addListener:()=>{},removeListener:()=>{},addEventListener:()=>{},removeEventListener:()=>{},dispatchEvent:()=>false})});
globalThis.ResizeObserver=class {observe(){}unobserve(){}disconnect(){}};
const computedStyle=window.getComputedStyle;
window.getComputedStyle=(element)=>computedStyle(element);
// Ant Design 的 useDebounce 会在卸载后留下 10ms 状态定时器；在 jsdom 关闭前排空。
import {cleanup} from '@testing-library/react';
afterEach(async()=>{cleanup();await new Promise(resolve=>setTimeout(resolve,20))});

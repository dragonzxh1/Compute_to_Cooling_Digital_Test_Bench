// Scope the embedded SVG styles so the dark P&ID cannot recolor chart labels.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
const pkg='D:/Github/c2c-evidence-review/memphis-00-01-hydraulic-v1/run39912648335/reviewed-delivery';
const svgFile=path.join(pkg,'12_PHYSICAL_HYDRAULIC_PID.svg'),htmlFile=path.join(pkg,'15_INTERACTIVE_REPORT.html');
const old=fs.readFileSync(svgFile,'utf8');if(old.includes('class="pid"'))throw Error('ALREADY_SCOPED');
const updated=old.replace('<svg xmlns=','<svg class="pid" xmlns=').replace('<style>text{','<style>.pid text{').replace('}.tiny{','}.pid .tiny{');
const html=fs.readFileSync(htmlFile,'utf8');if(!html.includes(old))throw Error('SVG_EMBED_MISMATCH');
fs.writeFileSync(svgFile,updated);fs.writeFileSync(htmlFile,html.replace(old,updated));

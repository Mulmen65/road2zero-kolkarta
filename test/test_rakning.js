// Kontroll: sidans räkning med standardvärden ska ge analysens resultat (v4, 11 nov 2026) inom 2 %.
const fs=require('fs'), path=require('path');
const html=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8');
const src=html.match(/function rakna[\s\S]*?\n}\n/)[0];
let typVal={}; const rakna=eval('('+src.replace('function rakna','function')+')');
const omr=JSON.parse(fs.readFileSync(path.join(__dirname,'..','data','omraden.geojson'))).features;
const P={dBl:64,uBl:0.05,dSm:11,uSm:0.71,arb:25/90,rest:22,tradAndel:0,tradTak:50,verksHela:true};
const sum=omr.reduce((s,f)=>s+rakna(f.properties,P).kt,0);
const sm=omr.reduce((s,f)=>s+rakna({...f.properties,typ:'smahus'},P).kt,0);
console.log('blandad', sum.toFixed(1), 'kt (analysen 153,4); småhus', sm.toFixed(1), 'kt (analysen 67,5)');
const ok=Math.abs(sum-153.4)/153.4<0.02 && Math.abs(sm-67.5)/67.5<0.03;
console.log(ok?'OK':'AVVIKER'); process.exit(ok?0:1);

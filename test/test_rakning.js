// Kontroll: sidans räkning med standardvärden ska ge referensresultatet inom 2 %.
// 153,4 kt i analysen 11 nov med ohårdgjord andel 0,05; 129,5 kt efter rättelsen till 0,20 (DeSO klippta mot land).
const fs=require('fs'), path=require('path');
const html=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8');
const src=html.match(/function rakna[\s\S]*?\n}\n/)[0];
let typVal={}; const rakna=eval('('+src.replace('function rakna','function')+')');
const omr=JSON.parse(fs.readFileSync(path.join(__dirname,'..','data','omraden.geojson'))).features;
const P={dBl:64,uBl:0.20,dSm:11,uSm:0.71,arb:25/90,rest:22,tradAndel:0,tradTak:50,verksHela:true};
const sum=omr.reduce((s,f)=>s+rakna(f.properties,P).kt,0);
const sm=omr.reduce((s,f)=>s+rakna({...f.properties,typ:'smahus'},P).kt,0);
console.log('blandad', sum.toFixed(1), 'kt (referens 129,5); småhus', sm.toFixed(1), 'kt (analysen 67,5)');
const ok=Math.abs(sum-129.5)/129.5<0.02 && Math.abs(sm-67.5)/67.5<0.03;
console.log(ok?'OK':'AVVIKER'); process.exit(ok?0:1);

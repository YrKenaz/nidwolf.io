const {JSDOM,VirtualConsole}=require('jsdom');const fs=require('fs');
const vc=new VirtualConsole();vc.on('jsdomError',e=>console.log('JSDOM ERR',e.message.slice(0,300),(e.detail&&e.detail.stack||'').slice(0,400)));vc.on('error',e=>console.log('ERR',e));
const d=new JSDOM(fs.readFileSync(process.argv[2],'utf8'),{runScripts:'dangerously',virtualConsole:vc});
const doc=d.window.document;console.log('cards',doc.querySelectorAll('.card').length,'tiers',doc.querySelectorAll('.tier').length,'chips',doc.querySelectorAll('#chips .chip').length,'groups',doc.querySelectorAll('.grp').length);

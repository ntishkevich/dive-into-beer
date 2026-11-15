const fs=require('node:fs');const path=require('node:path');const http=require('node:http');const zlib=require('node:zlib');const crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');const port=Number(process.env.BEER_PREVIEW_PORT||4173);const cache=new Map();
const routes={'/':'index.html','/index.html':'index.html','/beer/':'index.html','/beer/index.html':'index.html','/beer-design-audit.html':'output/beer-design-audit.html'};
function startPreview(port){
 return http.createServer((req,res)=>{
 const pathname=new URL(req.url,'http://127.0.0.1').pathname;
 const file=routes[pathname];if(!file){res.writeHead(404);res.end('Not found');return;}
 const absolute=path.join(root,file);const stat=fs.statSync(absolute,{throwIfNoEntry:false});
 if(!stat?.isFile()){res.writeHead(404);res.end('Not found');return;}
 const mtime=stat.mtimeMs;
 let entry=cache.get(file);
 if(!entry||entry.mtime!==mtime){const body=fs.readFileSync(absolute);entry={mtime,body,gzip:zlib.gzipSync(body),sha:crypto.createHash('sha256').update(body).digest('hex')};cache.set(file,entry);}
 const gzip=/\bgzip\b/.test(req.headers['accept-encoding']||'');const body=gzip?entry.gzip:entry.body;
 res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Content-Length':body.length,'X-Artifact-Sha256':entry.sha,'Cache-Control':'no-cache','Vary':'Accept-Encoding',...(gzip?{'Content-Encoding':'gzip'}:{})});res.end(body);
 }).listen(port,'127.0.0.1');
}
if(require.main===module){
 const server=startPreview(port);
 server.on('listening',()=>console.log('Beer atlas: http://127.0.0.1:'+server.address().port+'/'));
}
module.exports={startPreview};

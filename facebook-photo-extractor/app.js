"use strict";
const q = id => document.getElementById(id);
const encode = new TextEncoder();
const state = {mode:"url",photos:[],cursor:"",pageId:"",busy:false,exportIndex:0};
function tell(message,type=""){q("status").textContent=message;q("status").dataset.type=type;}
function config(){
  const base=q("backend").value.trim().replace(/\/+$/,"");
  const key=q("key").value.trim();
  if(!/^https:\/\/[A-Za-z0-9.-]+(?::443)?(?:\/[A-Za-z0-9/_-]*)?$/.test(base))throw Error("Enter your HTTPS Vercel API URL first.");
  if(!key)throw Error("Enter your private extractor access key.");
  return {base,key};
}
async function api(path,options={}){
  const c=config();
  const headers=Object.assign({},options.headers,{"X-Extractor-Key":c.key});
  const response=await fetch(c.base+path,Object.assign({},options,{headers,cache:"no-store",credentials:"omit"}));
  if(!response.ok){
    let error="Request failed: HTTP "+response.status;
    try{const d=await response.json();error=d.error||error;}catch{}
    throw Error(error);
  }
  return response;
}
function lock(busy){
  state.busy=busy;
  for(const id of ["load","more","scan"])q(id).disabled=busy;
  q("zip").disabled=busy||!state.photos.length;
  q("clear").disabled=busy||!state.photos.length;
}
function clearAll(){
  state.photos=[];state.cursor="";state.pageId="";state.exportIndex=0;q("zip").textContent="Download ZIP";
  q("more").classList.add("hidden");
  q("total").textContent="0 photos found.";
  q("preview").className="empty";
  q("preview").replaceChildren(document.createTextNode("Photos will appear here after scanning."));
  q("progress").classList.add("hidden");q("detail").textContent="";
  lock(false);
}
function switchMode(mode){
  state.mode=mode;clearAll();tell("");
  q("urlTab").setAttribute("aria-selected",String(mode==="url"));
  q("fileTab").setAttribute("aria-selected",String(mode==="file"));
  q("urlMode").classList.toggle("hidden",mode!=="url");
  q("fileMode").classList.toggle("hidden",mode!=="file");
}
q("urlTab").addEventListener("click",()=>switchMode("url"));
q("fileTab").addEventListener("click",()=>switchMode("file"));
q("clear").addEventListener("click",()=>{clearAll();tell("");});
function draw(){
  const unique=new Map();
  for(const p of state.photos){if(p.id&&!unique.has(p.id))unique.set(p.id,p);}
  state.photos=[...unique.values()].slice(0,1500);
  q("total").textContent=state.photos.length+" photo(s) found; ZIP export attempts all accessible images.";
  const gallery=document.createElement("div");gallery.className="grid";gallery.id="preview";
  for(const p of state.photos.slice(0,90)){
    const tile=document.createElement("div");tile.className="tile";
    const image=document.createElement("img");image.src=p.preview||p.url||"";
    image.alt="Photo "+p.id;image.loading="lazy";image.referrerPolicy="no-referrer";
    const caption=document.createElement("span");caption.textContent=p.id;
    tile.append(image,caption);gallery.append(tile);
  }
  q("preview").replaceWith(gallery);
  lock(false);
}
async function loadPage(cursor=""){
  lock(true);tell("Checking your Meta API permissions...");
  try{
    const payload=cursor?{pageId:state.pageId,after:cursor}:{pageUrl:q("page").value.trim()};
    const res=await api("/api/facebook-photos",{
      method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)
    });
    const found=await res.json();
    if(!cursor){state.photos=[];state.pageId=found.pageId;}
    state.photos.push(...(found.photos||[]).map(p=>({
      id:String(p.id),preview:p.preview||"",mode:"url",caption:p.caption||""
    })));
    state.cursor=found.nextCursor||"";
    q("more").classList.toggle("hidden",!state.cursor||state.photos.length>=1500);
    draw();
    tell(state.photos.length?state.photos.length+" photos found. "+(state.cursor?"Load more for the next page.":"No further pages available."):"No accessible uploaded Page photos found.","ok");
  }catch(e){tell(e.message,"error");lock(false);}
}
q("load").addEventListener("click",()=>loadPage(""));
q("more").addEventListener("click",()=>loadPage(state.cursor));

function findImages(text){
  // Parse only Facebook CDN image URLs. Do not upload the local HTML or decode session tokens.
  const flat=text.replace(/\\u([0-9a-f]{4})/gi,(_,x)=>String.fromCharCode(parseInt(x,16)))
    .replace(/\\\//g,"/").replace(/&amp;/gi,"&").replace(/&#38;/g,"&");
  const rawUrls=flat.match(/https?:\/\/[^\s<>"'\\]+/gi)||[];
  const found=new Map();
  for(const raw of rawUrls){
    let url;
    try{url=new URL(raw.replace(/[),;]+$/,""));}catch{continue;}
    if(url.protocol!=="https:")continue;
    const host=url.hostname.toLowerCase();
    if(!host.startsWith("scontent.")||!host.endsWith(".fbcdn.net"))continue;
    if(!/\.(?:jpg|jpeg|png|webp|gif)$/i.test(url.pathname))continue;
    const identity=host+url.pathname;
    const old=found.get(identity);
    const score=(url.searchParams.has("stp")?0:100)+(url.href.includes("s2048")?50:0);
    if(!old||old.score<score)found.set(identity,{url:url.href,score});
  }
  return [...found.values()].slice(0,1500).map((p,index)=>({
    id:"saved-"+String(index+1).padStart(3,"0"),mode:"file",
    caption:"Imported image "+(index+1),url:p.url,preview:p.url
  }));
}
q("scan").addEventListener("click",async()=>{
  const file=q("local").files[0];
  if(!file){tell("Choose a saved .html or .txt file first.","error");return;}
  if(file.size>35*1024*1024){tell("Your saved file exceeds the 35 MB limit.","error");return;}
  lock(true);tell("Reading file locally. No HTML is uploaded.");
  try{
    state.photos=findImages(await file.text());
    state.exportIndex=0;
    q("zip").textContent="Download ZIP";
    draw();tell(state.photos.length+" image URLs found. Some may be thumbnails or have expired.","ok");
  }catch(e){tell(e.message,"error");lock(false);}
});
// Browser-only ZIP writer (store method). No external ZIP library or upload is necessary.
const crcTable=(()=>{
  const t=new Uint32Array(256);
  for(let i=0;i<256;i++){let c=i;for(let j=0;j<8;j++)c=(c&1)?(0xedb88320^(c>>>1)):(c>>>1);t[i]=c>>>0;}
  return t;
})();
function checksum(bytes){let c=0xffffffff;for(const b of bytes)c=crcTable[(c^b)&255]^(c>>>8);return(c^0xffffffff)>>>0;}
function w16(dst,p,n){dst[p]=n&255;dst[p+1]=(n>>>8)&255;}
function w32(dst,p,n){w16(dst,p,n);w16(dst,p+2,n>>>16);}
function zipFiles(files){
  const chunks=[],directory=[];let offset=0;
  for(const item of files){
    const name=encode.encode(item.name),body=item.bytes,crc=checksum(body);
    const header=new Uint8Array(30+name.length);
    w32(header,0,0x04034b50);w16(header,4,20);w16(header,6,0x0800);
    w32(header,14,crc);w32(header,18,body.length);w32(header,22,body.length);
    w16(header,26,name.length);header.set(name,30);
    const record=new Uint8Array(46+name.length);
    w32(record,0,0x02014b50);w16(record,4,20);w16(record,6,20);w16(record,8,0x0800);
    w32(record,16,crc);w32(record,20,body.length);w32(record,24,body.length);
    w16(record,28,name.length);w32(record,42,offset);record.set(name,46);
    chunks.push(header,body);directory.push(record);offset+=header.length+body.length;
  }
  const end=new Uint8Array(22),length=directory.reduce((x,item)=>x+item.length,0);
  w32(end,0,0x06054b50);w16(end,8,files.length);w16(end,10,files.length);
  w32(end,12,length);w32(end,16,offset);
  return new Blob([...chunks,...directory,end],{type:"application/zip"});
}
async function photoFile(photo){
  if(photo.mode==="url"){
    const response=await api("/api/facebook-image?id="+encodeURIComponent(photo.id));
    return response.blob();
  }
  if(q("backend").value.trim()&&q("key").value.trim()){
    const response=await api("/api/imported-image",{
      method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:photo.url})
    });
    return response.blob();
  }
  // Most Facebook CDN images do not enable browser CORS; the backend is preferred.
  const response=await fetch(photo.url,{credentials:"omit",mode:"cors"});
  if(!response.ok)throw Error("Image link unavailable.");
  return response.blob();
}
q("zip").addEventListener("click",async()=>{
  if(!state.photos.length)return;
  lock(true);q("progress").classList.remove("hidden");q("bar").style.width="0%";
  const photos=[],errors=[];let size=0;
  const start=state.exportIndex, end=Math.min(start+75,state.photos.length);
  for(let i=start;i<end;i++){
    const photo=state.photos[i];
    try{
      const blob=await photoFile(photo);
      if(!blob.type.startsWith("image/")||blob.size>25*1024*1024)throw Error("Unsupported photo or over 25 MB");
      if(size+blob.size>180*1024*1024)throw Error("ZIP memory limit 180 MB reached");
      const ext=blob.type.includes("png")?"png":blob.type.includes("webp")?"webp":blob.type.includes("gif")?"gif":"jpg";
      photos.push({name:"photos/photo-"+String(i+1).padStart(3,"0")+"."+ext,bytes:new Uint8Array(await blob.arrayBuffer())});
      size+=blob.size;
    }catch(e){errors.push({photo:photo.id,error:String(e.message).slice(0,120)});}
    q("bar").style.width=Math.round((i-start+1)/(end-start)*100)+"%";
    q("detail").textContent="Processed "+(i+1)+"/"+state.photos.length+" · "+photos.length+" downloaded · "+errors.length+" failed";
  }
  const manifest={created:new Date().toISOString(),source:state.mode,range:[start+1,end],requested:end-start,succeeded:photos.length,errors};
  photos.push({name:"manifest.json",bytes:encode.encode(JSON.stringify(manifest,null,2))});
  const href=URL.createObjectURL(zipFiles(photos));
  const anchor=document.createElement("a");anchor.href=href;anchor.download="facebook-page-photos-part-"+String(Math.floor(start/75)+1).padStart(2,"0")+".zip";
  document.body.append(anchor);anchor.click();anchor.remove();
  setTimeout(()=>URL.revokeObjectURL(href),60000);
  state.exportIndex=end<state.photos.length?end:0;
  q("zip").textContent=state.exportIndex?"Download next ZIP ("+(state.exportIndex+1)+"–"+Math.min(state.exportIndex+75,state.photos.length)+")":"Download ZIP again";
  tell((photos.length-1)+" photos exported from this batch. "+errors.length+" failures are listed in manifest.json."+(state.exportIndex?" Click Download next ZIP to continue.":" All loaded photos processed."),errors.length?"error":"ok");
  lock(false);
});

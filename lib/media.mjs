const signatures={
 'image/png':bytes=>[137,80,78,71,13,10,26,10].every((n,i)=>bytes[i]===n),
 'image/jpeg':bytes=>bytes[0]===255&&bytes[1]===216&&bytes[2]===255,
 'image/webp':bytes=>String.fromCharCode(...bytes.slice(0,4))==='RIFF'&&String.fromCharCode(...bytes.slice(8,12))==='WEBP',
 'video/mp4':bytes=>String.fromCharCode(...bytes.slice(4,8))==='ftyp',
 'video/webm':bytes=>[26,69,223,163].every((n,i)=>bytes[i]===n)
};
export function inspectMedia(bytes,mime,size){
 const kind=mime.startsWith('image/')?'image':'video';
 if(!signatures[mime]||!signatures[mime](bytes)||size<12||size>(kind==='image'?8:25)*1024*1024)throw new Error('Choose a valid JPEG, PNG or WebP up to 8 MB, or MP4/WebM up to 25 MB.');
 return {kind,extension:mime.split('/')[1]==='jpeg'?'jpg':mime.split('/')[1]};
}

import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
export async function mountCat(stage,{reduced=false}={}){
 const canvas=stage.querySelector('canvas');
 const renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true,powerPreference:'low-power'});
 renderer.setPixelRatio(Math.min(devicePixelRatio,1.65));renderer.setClearColor(0x000000,0);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.18;
 renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFShadowMap;
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(31,1,.1,80);
 camera.position.set(0,2.12,8.9);camera.lookAt(0,1.8,0);
 const hemi=new THREE.HemisphereLight(0xf4f1ff,0x8074a1,3.2);scene.add(hemi);
 const key=new THREE.DirectionalLight(0xfff6ff,4.2);key.position.set(-3,5,6);key.castShadow=true;key.shadow.mapSize.set(1024,1024);Object.assign(key.shadow.camera,{left:-3,right:3,top:5,bottom:-2,near:.1,far:20});key.shadow.bias=-.0004;key.shadow.normalBias=.018;key.shadow.radius=4;scene.add(key);
 const fill=new THREE.DirectionalLight(0xc0b1ff,2.2);fill.position.set(4,3,-3);scene.add(fill);
 const soft=new THREE.PointLight(0xffffff,3.5,15,2);soft.position.set(1,3,4);scene.add(soft);
 const floor=new THREE.Mesh(new THREE.PlaneGeometry(18,18),new THREE.ShadowMaterial({opacity:.065}));floor.rotation.x=-Math.PI/2;floor.position.y=-.015;floor.receiveShadow=true;scene.add(floor);
 const gltf=await new GLTFLoader().loadAsync(stage.dataset.model),model=gltf.scene;
 model.scale.setScalar(10.5);model.position.set(-.11,0,0);model.rotation.y=-.10;model.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;if(o.material){o.material.envMapIntensity=.7;}}});scene.add(model);
 const head=model.getObjectByName('HeadPivot');if(!head)throw new Error('Head pivot missing');
 let paused=false,visible=true,inView=true,last=0,elapsed=0,nod=0,nodEnd=0,target={x:0,y:0},look={x:0,y:0};
 const setPointer=(x,y)=>{target.x=THREE.MathUtils.clamp((x/innerWidth-.5)*2,-1,1);target.y=THREE.MathUtils.clamp((y/innerHeight-.5)*2,-1,1);};
 const move=e=>{if(e.pointerType==='mouse'||e.pointerType==='pen')setPointer(e.clientX,e.clientY);else if(stage.contains(e.target)){const r=stage.getBoundingClientRect();target.x=THREE.MathUtils.clamp((e.clientX-r.left)/r.width*2-1,-1,1);target.y=THREE.MathUtils.clamp((e.clientY-r.top)/r.height*2-1,-1,1);}};
 const reset=()=>{target.x=0;target.y=0;};
 window.addEventListener('pointermove',move,{passive:true});stage.addEventListener('pointerdown',move,{passive:true});document.documentElement.addEventListener('pointerleave',reset);stage.addEventListener('pointerup',e=>{if(e.pointerType!=='mouse')setTimeout(reset,1000);});
 function resize(){const w=stage.clientWidth,h=stage.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;const targetHeight=4.15;const neededDistance=targetHeight/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov)/2));camera.position.z=Math.max(neededDistance,3.05/(2*Math.tan(THREE.MathUtils.degToRad(camera.fov)/2)*camera.aspect));camera.updateProjectionMatrix();render(0);}
 function render(dt){if(!paused&&!reduced){const damping=1-Math.exp(-dt*8);look.x=THREE.MathUtils.lerp(look.x,target.x,damping);look.y=THREE.MathUtils.lerp(look.y,target.y,damping);head.rotation.y=look.x*.26;head.rotation.x=look.y*.14;head.rotation.z=-look.x*.045+Math.sin(elapsed*1.2)*.012;if(nodEnd>elapsed){const progress=(elapsed-nod)/(nodEnd-nod);head.rotation.x+=Math.sin(progress*Math.PI*4)*.09*Math.sin(progress*Math.PI);}model.scale.y=10.5*(1+Math.sin(elapsed*1.7)*.004);key.position.x=-3+look.x*.8+Math.sin(elapsed*.4)*.18;soft.position.x=1+look.x*.9;fill.intensity=2.2+Math.sin(elapsed*.65)*.12;}else if(reduced){head.rotation.set(0,0,0);model.scale.y=10.5;key.position.x=-3;fill.intensity=2.2;}
 renderer.render(scene,camera);}
 function loop(time){const dt=Math.min((time-last)/1000,.05);last=time;if(!visible||!inView||paused||reduced)return;elapsed+=dt;render(dt);}
 renderer.setAnimationLoop(loop);const observer=new ResizeObserver(resize);observer.observe(stage);const intersection=new IntersectionObserver(entries=>{inView=entries[0].isIntersecting;},{rootMargin:'100px'});intersection.observe(stage);document.addEventListener('visibilitychange',()=>{visible=!document.hidden;last=performance.now();});resize();stage.classList.add('is-ready');
 return {greet(){target.x=0;target.y=-.2;nod=elapsed;nodEnd=elapsed+1.1;},setPaused(value){paused=value;render(0);},setReduced(value){reduced=value;render(0);}};
}

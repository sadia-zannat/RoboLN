'use client';
import {usePathname,useRouter} from 'next/navigation';
import {useEffect,useState} from 'react';
import {logicalParent} from '@/lib/navigation';
// Native history is authoritative; indexed state identifies whether forward entries exist.
// This only tracks destinations inside the current RoboLN tab, not external browser entries.
export function useNavHistory(){
  const path=usePathname();const router=useRouter();
  const [index,setIndex]=useState(0);const [max,setMax]=useState(0);
  useEffect(()=>{
    const oldPush=history.pushState.bind(history);const oldReplace=history.replaceState.bind(history);
    let current=Number(history.state?.__robolnIndex ?? 0);
    let highest=Number(sessionStorage.getItem('roboln-history-max') ?? current);
    oldReplace({...history.state,__robolnIndex:current},'',location.href);
    setIndex(current);setMax(highest);
    history.pushState=function(data:unknown,unused:string,url?:string|URL|null){
      current+=1;highest=current;sessionStorage.setItem('roboln-history-max',String(highest));
      const v=oldPush({...((data&&typeof data==='object')?data:{}),__robolnIndex:current},unused,url);
      setIndex(current);setMax(highest);return v;
    };
    history.replaceState=function(data:unknown,unused:string,url?:string|URL|null){
      return oldReplace({...((data&&typeof data==='object')?data:{}),__robolnIndex:current},unused,url);
    };
    const popped=()=>{current=Number(history.state?.__robolnIndex??0);setIndex(current);setMax(highest);};
    window.addEventListener('popstate',popped);
    return()=>{history.pushState=oldPush;history.replaceState=oldReplace;window.removeEventListener('popstate',popped);};
  },[]);
  const back=()=>{if(index>0)router.back();else router.push(logicalParent(path));};
  const forward=()=>{if(index<max)window.history.forward();};
  return {back,forward,canForward:index<max,canBack:index>0,parent:logicalParent(path)};
}

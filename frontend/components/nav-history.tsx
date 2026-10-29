'use client';
import {usePathname,useRouter} from 'next/navigation';
import {useEffect,useRef,useState} from 'react';
import {logicalParent} from '@/lib/navigation';

type RouteStack={paths:string[];index:number};
const initial:RouteStack={paths:[],index:0};
/**
 * Track only in-app routes visited in this tab. Native browser popstate is the
 * authority for Back/Forward, while route changes record client-side pushes.
 * A direct deep link has no *known* previous in-app route and uses its parent.
 * Never use history.length to infer that a forward entry exists.
 */
export function useNavHistory(){
 const path=usePathname();
 const router=useRouter();
 const pendingPop=useRef(false);
 const stack=useRef<RouteStack>(initial);
 const [state,setState]=useState<RouteStack>(initial);

 useEffect(()=>{
  const pop=()=>{pendingPop.current=true;};
  window.addEventListener('popstate',pop);
  return()=>window.removeEventListener('popstate',pop);
 },[]);

 useEffect(()=>{
  const previous=stack.current;
  let next:RouteStack;
  if(previous.paths.length===0){
   next={paths:[path],index:0};
  }else if(previous.paths[previous.index]===path){
   pendingPop.current=false;
   return;
  }else if(pendingPop.current){
   // The URL has already moved through native session history.
   const before=previous.paths[previous.index-1];
   const after=previous.paths[previous.index+1];
   if(path===before)next={...previous,index:previous.index-1};
   else if(path===after)next={...previous,index:previous.index+1};
   else{
    const known=previous.paths.lastIndexOf(path);
    next=known>=0?{...previous,index:known}:{paths:[...previous.paths.slice(0,previous.index+1),path],index:previous.index+1};
   }
  }else{
   // A new Link/router.push truncates our known forward destinations.
   const paths=[...previous.paths.slice(0,previous.index+1),path];
   next={paths,index:paths.length-1};
  }
  pendingPop.current=false;
  stack.current=next;
  setState(next);
 },[path]);

 const back=()=>{
  if(state.index>0)window.history.back();
  else router.push(logicalParent(path));
 };
 const forward=()=>{if(state.index<state.paths.length-1)window.history.forward();};
 return {back,forward,canForward:state.index<state.paths.length-1,canBack:state.index>0,parent:logicalParent(path)};
}

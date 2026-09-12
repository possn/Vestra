/* Vestra Portfolio Collapsibles v1.2 — canonical portfolio section collapsing. */
(() => {
'use strict';
const COLLAPSE_KEY='vestra-market-collapse-v1';
const t=v=>String(v??'').trim();
function collapseState(){try{return JSON.parse(localStorage.getItem(COLLAPSE_KEY)||'{}')||{}}catch{return{}}}
function saveState(x){try{localStorage.setItem(COLLAPSE_KEY,JSON.stringify(x))}catch{}}
function keyFor(card,i){return t(card.querySelector('.market-perspective-head h4')?.textContent||card.querySelector(':scope > h4')?.textContent||card.querySelector('h4')?.textContent||`section-${i}`).toLowerCase().replace(/[^a-z0-9À-ÿ]+/gi,'-').replace(/^-|-$/g,'').slice(0,70)}
function setCollapsed(card,x){card.classList.toggle('is-collapsed',x);const b=card.querySelector(':scope > .market-collapse-toggle');if(b){b.textContent=x?'＋':'−';b.title=x?'Abrir secção':'Fechar secção'}}
function install(){const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');if(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)return;const st=collapseState(),cards=[...c.querySelectorAll('.market-detail-card')];cards.forEach((card,i)=>{if(card.classList.contains('market-decision-center')||card.dataset.collapsible==='1')return;card.dataset.collapsible='1';const k=keyFor(card,i);card.dataset.collapseKey=k;const b=document.createElement('button');b.type='button';b.className='market-collapse-toggle';b.dataset.collapseToggle=k;card.appendChild(b);const def=card.classList.contains('market-research-queue')||i>1;setCollapsed(card,st[k]===undefined?def:!!st[k])});if(!c.querySelector('.market-collapse-toolbar')){const bar=document.createElement('div');bar.className='market-collapse-toolbar';bar.innerHTML='<span>Secções</span><button type="button" data-collapse-all="open">Abrir tudo</button><button type="button" data-collapse-all="close">Fechar tudo</button>';const center=c.querySelector('.market-decision-center');center?center.insertAdjacentElement('afterend',bar):c.prepend(bar)}}
function style(){if(document.getElementById('vestra-portfolio-collapsibles-style'))return;const link=document.createElement('link');link.id='vestra-portfolio-collapsibles-style';link.rel='stylesheet';link.href='portfolio-collapsibles.css?v=1.0';document.head.appendChild(link)}
document.addEventListener('click',e=>{const b=e.target.closest?.('[data-collapse-toggle]');if(b){e.preventDefault();e.stopPropagation();const card=b.closest('.market-detail-card');const x=!card.classList.contains('is-collapsed');setCollapsed(card,x);const st=collapseState();st[card.dataset.collapseKey]=x;saveState(st);return}const all=e.target.closest?.('[data-collapse-all]');if(all){e.preventDefault();e.stopPropagation();const x=all.dataset.collapseAll==='close',st=collapseState();document.querySelectorAll('#marketSheetContent .market-detail-card[data-collapsible="1"]').forEach(card=>{setCollapsed(card,x);st[card.dataset.collapseKey]=x});saveState(st)}});
function start(){style();install()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
window.VestraPortfolioCollapsibles=Object.freeze({refresh:install,version:'1.2'});
})();

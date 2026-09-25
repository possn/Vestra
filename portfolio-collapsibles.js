/* Vestra Portfolio Collapsibles v1.6 — collapsed cards are direct, keyboard-accessible open targets. */
// Static Carteira secondary tools (including equity performance) are owned by index.html, not this market-sheet runtime.
(() => {
'use strict';
const COLLAPSE_KEY='vestra-market-collapse-v1';
const t=v=>String(v??'').trim();
function collapseState(){try{return JSON.parse(localStorage.getItem(COLLAPSE_KEY)||'{}')||{}}catch{return{}}}
function saveState(x){try{localStorage.setItem(COLLAPSE_KEY,JSON.stringify(x))}catch{}}
function keyFor(card,i){return t(card.querySelector('.market-perspective-head h4')?.textContent||card.querySelector(':scope > h4')?.textContent||card.querySelector('h4')?.textContent||`section-${i}`).toLowerCase().replace(/[^a-z0-9À-ÿ]+/gi,'-').replace(/^-|-$/g,'').slice(0,70)}
function setCollapsed(card,x){card.classList.toggle('is-collapsed',x);const b=card.querySelector(':scope > .market-collapse-toggle');if(b){b.textContent=x?'＋':'−';b.title=x?'Abrir secção':'Fechar secção';b.setAttribute('aria-label',x?'Abrir secção':'Fechar secção');b.setAttribute('aria-expanded',x?'false':'true')}}
function install(){const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');if(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)return;const st=collapseState(),cards=[...c.querySelectorAll('.market-detail-card')];cards.forEach((card,i)=>{if(card.classList.contains('market-decision-center')||card.dataset.collapsible==='1')return;card.dataset.collapsible='1';const k=keyFor(card,i);card.dataset.collapseKey=k;const b=document.createElement('button');b.type='button';b.className='market-collapse-toggle';b.dataset.collapseToggle=k;card.appendChild(b);const def=card.classList.contains('market-research-queue')||i>1;setCollapsed(card,st[k]===undefined?def:!!st[k])})}
function style(){if(document.getElementById('vestra-portfolio-collapsibles-style'))return;const link=document.createElement('link');link.id='vestra-portfolio-collapsibles-style';link.rel='stylesheet';link.href='portfolio-collapsibles.css?v=1.2';document.head.appendChild(link)}
function toggleCard(card){if(!card)return;const x=!card.classList.contains('is-collapsed');setCollapsed(card,x);const st=collapseState();st[card.dataset.collapseKey]=x;saveState(st)}
document.addEventListener('click',e=>{const b=e.target.closest?.('[data-collapse-toggle]');if(b){e.preventDefault();e.stopPropagation();toggleCard(b.closest('.market-detail-card'));return;}const card=e.target.closest?.('.market-detail-card[data-collapsible="1"].is-collapsed');if(!card||e.target.closest?.('a,button,input,select,textarea,[role="button"]'))return;e.preventDefault();toggleCard(card)});
function start(){style()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
window.VestraPortfolioCollapsibles=Object.freeze({refresh:install,version:'1.6'});
})();

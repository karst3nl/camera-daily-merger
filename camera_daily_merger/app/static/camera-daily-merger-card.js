/* Camera Daily Merger local Lovelace card. MIT license; no external dependencies. */
class CameraDailyMergerCard extends HTMLElement {
  constructor(){
    super();this.attachShadow({mode:'open'});this._generation=0;this._busy=false;this._ready=false;this._session=null;
    const style=document.createElement('style');style.textContent=':host{display:block}ha-card{display:block;overflow:hidden}.heading{padding:16px 20px;font:500 18px system-ui}.message{padding:0 20px 16px;font:14px system-ui;color:var(--secondary-text-color,#9aadb5)}iframe{display:block;width:100%;border:0;background:var(--card-background-color,#101719)}iframe[hidden]{display:none}';
    this._card=document.createElement('ha-card');this._heading=document.createElement('div');this._heading.className='heading';
    this._message=document.createElement('div');this._message.className='message';this._message.setAttribute('role','status');
    this._frame=document.createElement('iframe');this._frame.title='Camera Daily Merger recordings';this._frame.referrerPolicy='no-referrer';this._frame.setAttribute('allow','autoplay; fullscreen');this._frame.setAttribute('allowfullscreen','');this._frame.hidden=true;
    this._card.append(this._heading,this._message,this._frame);this.shadowRoot.append(style,this._card);
    this._visibility=()=>{if(!document.hidden)this._authenticate();};
  }
  setConfig(config){
    if(!config || typeof config.addon!=='string' || !/^[a-z0-9_]{1,128}$/.test(config.addon))throw new Error('Set addon to the installed Camera Daily Merger app slug.');
    const view=config.view || 'latest';if(!['latest','day'].includes(view))throw new Error('view must be latest or day.');
    if(config.date){let valid=false;try{valid=/^\d{4}-\d{2}-\d{2}$/.test(config.date) && new Date(config.date+'T00:00:00Z').toISOString().slice(0,10)===config.date;}catch{}if(!valid)throw new Error('date must be YYYY-MM-DD.');if(view!=='day')throw new Error('date is only supported with view: day.');}
    const height=config.height===undefined?640:Number(config.height);if(!Number.isInteger(height) || height<300 || height>1600)throw new Error('height must be 300..1600 pixels.');
    this._config={addon:config.addon,view,date:config.date || null,height,title:typeof config.title==='string'?config.title.slice(0,100):'Camera Daily Merger'};
    this._heading.textContent=this._config.title;this._frame.height=String(height);this._reset();this._authenticate();
  }
  set hass(hass){
    const changed=this._hass && (this._connection!==hass.connection || this._userId!==hass.user?.id);
    this._connection=hass.connection;this._userId=hass.user?.id;this._hass=hass;if(changed)this._reset();if(!this._ready)this._authenticate();
  }
  connectedCallback(){document.addEventListener('visibilitychange',this._visibility);this._timer=setInterval(()=>{if(!document.hidden)this._authenticate();},60000);this._authenticate();}
  disconnectedCallback(){document.removeEventListener('visibilitychange',this._visibility);clearInterval(this._timer);this._generation++;this._busy=false;this._ready=false;this._session=null;this._frame.removeAttribute('src');this._frame.hidden=true;}
  getCardSize(){return Math.ceil(((this._config?.height || 640)+70)/50);}
  static getStubConfig(){return {addon:'ADDON_SLUG',view:'latest',height:640};}
  _reset(){this._generation++;this._busy=false;this._ready=false;this._session=null;this._frame.hidden=true;this._frame.removeAttribute('src');}
  async _request(hass,modern,legacy){
    try{return await hass.callWS(modern);}catch(error){if(error?.code==='unknown_command')return hass.callWS(legacy);throw error;}
  }
  _cookie(session){
    if(typeof session!=='string' || !/^[a-zA-Z0-9._-]{1,512}$/.test(session))throw new Error('Invalid ingress session response.');
    document.cookie=`ingress_session=${session};path=/api/hassio_ingress/;SameSite=Strict${location.protocol==='https:'?';Secure':''}`;
  }
  async _authenticate(){
    if(!this.isConnected || !this._config || !this._hass || this._busy)return;
    this._busy=true;const generation=this._generation;const hass=this._hass;const config=this._config;
    const current=()=>this.isConnected && generation===this._generation;
    try{
      if(this._ready && this._session){
        try{await this._request(hass,{type:'supervisor/ingress/validate_session',session:this._session},{type:'supervisor/api',endpoint:'/ingress/validate_session',method:'post',data:{session:this._session}});if(current())this._message.textContent='';return;}catch{/* Recreate an expired session through the authenticated HA connection. */}
      }
      if(current())this._message.textContent='Connecting through Home Assistant ingress…';
      const info=await this._request(hass,{type:'supervisor/ingress/info',slug:config.addon},{type:'supervisor/api',endpoint:`/addons/${config.addon}/info`,method:'get'});
      const target=new URL(info.ingress_url,location.origin);
      if(!info.ingress_url || target.origin!==location.origin || !/^\/api\/hassio_ingress\/[a-zA-Z0-9_-]+\/?$/.test(target.pathname) || target.search || target.hash || (info.state && info.state!=='started'))throw new Error('App ingress unavailable.');
      const response=await this._request(hass,{type:'supervisor/ingress/session',slug:config.addon},{type:'supervisor/api',endpoint:'/ingress/session',method:'post'});
      if(!current())return;
      this._cookie(response.session);this._session=response.session;
      target.pathname=target.pathname.replace(/\/?$/,'/');
      const hash=new URLSearchParams({view:config.view,embed:'1'});if(config.date)hash.set('day',config.date);target.hash=hash.toString();
      const source=target.pathname+target.hash;
      if(this._ready && this._frame.getAttribute('src')===source)this._frame.contentWindow.location.reload();else this._frame.src=source;
      this._frame.hidden=false;this._ready=true;this._message.textContent='';
    }catch{
      if(current())this._message.textContent='Cannot open app ingress. Check the app slug, that the app is running, and your Home Assistant permissions. Use an admin account with the default app policy.';
    }finally{if(current())this._busy=false;}
  }
}
if(!customElements.get('camera-daily-merger-card'))customElements.define('camera-daily-merger-card',CameraDailyMergerCard);
window.customCards=window.customCards || [];
if(!window.customCards.some(card=>card.type==='camera-daily-merger-card'))window.customCards.push({type:'camera-daily-merger-card',name:'Camera Daily Merger',description:'Latest-per-camera or same-day recordings through authenticated app ingress.',preview:false});

// Stereotaxic viewer globals
var	LR=45,PA=54,IS=45;
var sum=new Uint16Array(LR*PA*IS);
var	view=2;
var offcn=document.createElement('canvas');
var offtx=offcn.getContext('2d');
var tmpl_offcn=document.createElement('canvas');
var tmpl_offtx=tmpl_offcn.getContext('2d');
var canvas = document.getElementById('brainCanvas');
var ctx = canvas.getContext('2d');
var px,tmpl_px;
var	W,H;
var	tmpl_W,tmpl_H;
var	max=0;	// maximum value in volume
var	tmpl_LR=180,tmpl_PA=216,tmpl_IS=180;
var	slice=50;
var	template=0;
var	flagLocationsLoaded,nLocationsLoaded;
var	negpos=[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.0053,0.0105,0.0158,0.0211,0.0263,0.0316,0.0368,0.0421,0.0474,0.0526,0.0579,0.0632,0.0684,0.0737,0.0789,0.0842,0.0895,0.0947,0.1000,0.1053,0.1105,0.1158,0.1211,0.1263,0.1316,0.1368,0.1421,0.1474,0.1526,0.1579,0.1632,0.3368,0.3474,0.3579,0.3684,0.3789,0.3895,0.4000,0.4105,0.4211,0.4316,0.4421,0.4526,0.4632,0.4737,0.4842,0.4947,0.5053,0.5158,0.5263,0.5368,0.5474,0.5579,0.5684,0.5789,0.5895,0.6000,0.6105,0.6211,0.6316,0.6421,0.6526,0.6632,0.6737,0.6842,0.6947,0.7053,0.7158,0.7263,0.7368,0.7474,0.7579,0.7684,0.7789,0.7895,0.8000,0.8105,0.8211,0.8316,0.8421,0.8526,0.8632,0.8737,0.8842,0.8947,0.9053,0.9158,0.9263,0.9368,0.9474,0.9579,0.9684,0.9789,0.9895,1.0000,
		0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0.3316,0.3263,0.3211,0.3158,0.3105,0.3053,0.3000,0.2947,0.2895,0.2842,0.2789,0.2737,0.2684,0.2632,0.2579,0.2526,0.2474,0.2421,0.2368,0.2316,0.2263,0.2211,0.2158,0.2105,0.2053,0.2000,0.1947,0.1895,0.1842,0.1789,0.1737,0.1684,0.3263,0.3158,0.3053,0.2947,0.2842,0.2737,0.2632,0.2526,0.2421,0.2316,0.2211,0.2105,0.2000,0.1895,0.1789,0.1684,0.1579,0.1474,0.1368,0.1263,0.1158,0.1053,0.0947,0.0842,0.0737,0.0632,0.0526,0.0421,0.0316,0.0211,0.0105,0,0,0.0105,0.0211,0.0316,0.0421,0.0526,0.0632,0.0737,0.0842,0.0947,0.1053,0.1158,0.1263,0.1368,0.1474,0.1579,0.1684,0.1789,0.1895,0.2000,0.2105,0.2211,0.2316,0.2421,0.2526,0.2632,0.2737,0.2842,0.2947,0.3053,0.3158,0.3263,0.1684,0.1737,0.1789,0.1842,0.1895,0.1947,0.2000,0.2053,0.2105,0.2158,0.2211,0.2263,0.2316,0.2368,0.2421,0.2474,0.2526,0.2579,0.2632,0.2684,0.2737,0.2789,0.2842,0.2895,0.2947,0.3000,0.3053,0.3105,0.3158,0.3211,0.3263,0.3316,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
		1.0000,0.9895,0.9789,0.9684,0.9579,0.9474,0.9368,0.9263,0.9158,0.9053,0.8947,0.8842,0.8737,0.8632,0.8526,0.8421,0.8316,0.8211,0.8105,0.8000,0.7895,0.7789,0.7684,0.7579,0.7474,0.7368,0.7263,0.7158,0.7053,0.6947,0.6842,0.6737,0.6632,0.6526,0.6421,0.6316,0.6211,0.6105,0.6000,0.5895,0.5789,0.5684,0.5579,0.5474,0.5368,0.5263,0.5158,0.5053,0.4947,0.4842,0.4737,0.4632,0.4526,0.4421,0.4316,0.4211,0.4105,0.4000,0.3895,0.3789,0.3684,0.3579,0.3474,0.3368,0.1632,0.1579,0.1526,0.1474,0.1421,0.1368,0.1316,0.1263,0.1211,0.1158,0.1105,0.1053,0.1000,0.0947,0.0895,0.0842,0.0789,0.0737,0.0684,0.0632,0.0579,0.0526,0.0474,0.0421,0.0368,0.0316,0.0263,0.0211,0.0158,0.0105,0.0053,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0];
var searchString;

// Translucent viewer globals
var meshCanvas=document.getElementById('meshCanvas');	// translucent
var	cmap, volume=new Float32Array(45*54*45);			// translucent
var	flagDataLoaded=false;				// translucent
var brainmesh;							// translucent
var	level=0.5;							// translucent
var cube_edges = new Int32Array(24);	// surfacenets
var edge_table = new Int32Array(256);	// surfacenets
var buffer = new Int32Array(4096);		// surfacenets
var scene, renderer, composer;			// threejs
var camera, cameraControl;				// threejs
var geometry, surfacemesh, wiremesh;	// threejs

function setSearchString(str)
{
	searchString=str;
}
function initSearch() {
	configureInterface();
	configureTemplateImage();
	configureLocationsImage();
	loadTemplate();
	initTranslucent();
	loadLocations();
}
function configureInterface() {
	$('#toggle-selection').click(function() {
		$(this).prop('checked',!($(this).prop('checked')));
		$('input[type=checkbox]').each(function(){$(this).prop('checked',!($(this).prop('checked')))});
	});
	$('#add-to-collections').click(function() {
		// Article list manipulation allows the user to:
		// * add articles to a new article list
		// * append them to an old one
		// * display articles in article list
		// (not here: remove articles from a article list)
		// (not here: remove a article list)

		// Get selected articles
		var arr=[];
		$(".paper-stuff").each(function() {
			var parent=this;
			$(parent).find("input").each(function(){
				if($(this).prop('checked')==true) {
					$(parent).find("a").each(function(){
						var obj=parseInt($(this).attr('href').match(/\d+/)[0]);
						arr.push(obj);
					});
				}
			});
		});

		// Ask whether to add to new article list or to append to existing one
		var height=$('#add-to-collections').parent().height();
		var pos=$('#add-to-collections').offset();
		
		// create overlay
		var overlay=$("<div>");
		overlay.html(" ");
		overlay.css({
			position:"fixed",
			top:0,
			left:0,
			width:"100%",
			height:"100%",
			zIndex:9
		});
		overlay.click(function() {
			overlay.remove();
			win.remove();
		});
		$("body").append(overlay);
		
		// create dialog box
		var win=$("<div>");
		var con=[];
		if(collections.length) {
			con=con.concat([
				"<div style='padding:5'>",
				"<b>Add to</b><br/>"
			]);
			for(var i=0;i<collections.length;i++)
				con=con.concat("<a class='old-collection'>"+collections[i].name+"</a><br/>");
			con=con.concat(["</div>","<hr>"]);
		}
		con=con.concat([
			"<div style='padding:5'>",
			"<a class='new-collection'><b>Create new article collection...</b></a>",
			"</div>"
		]);
		win.append(con.join("\n"));
		win.css({
			position:"absolute",
			top:height+5,
			left:0, //pos.left,
			width: 200,
			textAlign:"left",
			border:"thin solid lightGrey",
			boxShadow:"2px 2px 10px rgba(0,0,0,.7)",
			background:"white",
			zIndex:10
		});
		$('#add-to-collections').css("position","relative");
		$('#add-to-collections').append(win);
		
		// Actions
		
		// append articles to an existing collection
		win.find("a.old-collection").click(function(e) {
			e.stopPropagation();
			var collectionName=$(this).text();
			for(var i=0;i<collections.length;i++) {
				if(collections[i].name==collectionName) {
					for(var j=0;j<arr.length;j++) {
						if(collections[i].articles.indexOf(arr[j])==-1)
							collections[i].articles.push(arr[j]);
					}
					logCollections(); // update collection in DB
				}
			}
			win.remove();
			overlay.remove();			
		});
		
		// create a new collection with the selected articles
		win.find("a.new-collection").click(function(e) {
			e.stopPropagation();
			if(arr.length==0) {
				alert("No selected articles");
			} else {
				var collectionName=prompt("Create new collection with "+arr.length+" articles");
				collections.push({name:collectionName,articles:arr});
				logCollections(); // update collection in DB
			}
			win.remove();
			overlay.remove();			
			updateCollections();
		});
	});
}
// Stereotaxic viewer
function changeView(theView)
{
	switch(theView)
	{
		case 'sagittal':
			view=0;
			break;
		case 'coronal':
			view=1;
			break;
		case 'axial':
			view=2;
			break;
	}
	configureTemplateImage();
	configureLocationsImage();
	drawImages();
}
function changeSlice(val)
{
	slice=val;
	drawImages();
}

function configureTemplateImage()
{
	// init query image
	switch(view)
	{	case 0:	tmpl_W=tmpl_PA; tmpl_H=tmpl_IS; break; // sagital
		case 1:	tmpl_W=tmpl_LR; tmpl_H=tmpl_IS; break; // coronal
		case 2:	tmpl_W=tmpl_LR; tmpl_H=tmpl_PA; break; // axial
	}
	tmpl_offcn.width=tmpl_W;
	tmpl_offcn.height=tmpl_H;
	tmpl_px=tmpl_offtx.getImageData(0,0,tmpl_W,tmpl_H);
}
function configureLocationsImage()
{
	// init query image
	switch(view)
	{	case 0:	W=PA; H=IS; break; // sagital
		case 1:	W=LR; H=IS; break; // coronal
		case 2:	W=LR; H=PA; break; // axial
	}
	offcn.width=W;
	offcn.height=H;
	px=offtx.getImageData(0,0,offcn.width,offcn.height);
	ctx.canvas.height=384;//ctx.canvas.width*H/W;
}
function drawImages()
{
	ctx.clearRect(0,0,ctx.canvas.width,canvas.height);
	
	// draw template
	if(template)
	{
		drawTemplateImage();
		ctx.globalAlpha = 0.8;
		ctx.globalCompositeOperation = "lighter";
	}
	
	// draw locations
	drawLocationsImage();
	
	// draw slice MNI coordinate
	ctx.globalCompositeOperation = "source-over";
	ctx.font = "14px sans-serif";
	ctx.textAlign = "end";
	ctx.textBaseline = "top";
	ctx.fillStyle="#fff";
	switch(view)
	{
		case 0: c="X";y=Math.round(tmpl_LR*slice/100)-88; break;
		case 1: c="Y";y=Math.round(tmpl_PA*slice/100)-124; break;
		case 2:	c="Z";y=Math.round(tmpl_IS*slice/100)-70; break;
	}
	ctx.fillText(c+": "+y,ctx.canvas.width,1);

	if(flagLocationsLoaded==0)
	{
		ctx.textAlign = "start";
		//ctx.fillText("Loading: "+nLocationsLoaded+"%",1,1);
	}
}
function drawTemplateImage()
{
	if(template==0)
		return;
	ys=Math.floor(tmpl_LR*slice/100);
	yc=Math.floor(tmpl_PA*slice/100);
	ya=Math.floor(tmpl_IS*slice/100);
	for(y=0;y<tmpl_H;y++)
	for(x=0;x<tmpl_W;x++)
	{
		switch(view)
		{	case 0:i=y*tmpl_PA*tmpl_LR+x*tmpl_LR+ys; break;
			case 1:i=y*tmpl_PA*tmpl_LR+yc*tmpl_LR+x; break;
			case 2:i=ya*tmpl_PA*tmpl_LR+y*tmpl_LR+x; break;
		}
		val=template[i];
		i=((tmpl_H-y-1)*tmpl_offcn.width+x)*4;
		tmpl_px.data[ i ]  =val;
		tmpl_px.data[ i+1 ]=val;
		tmpl_px.data[ i+2 ]=val;
		tmpl_px.data[ i+3 ]=255;
	}
	tmpl_offtx.putImageData(tmpl_px, 0, 0);
	ctx.drawImage(tmpl_offcn,0,canvas.height-canvas.width*tmpl_H/tmpl_W,ctx.canvas.width,canvas.width*tmpl_H/tmpl_W);
}
function drawLocationsImage()
{
	ys=Math.floor(LR*slice/100);
	yc=Math.floor(PA*slice/100);
	ya=Math.floor(IS*slice/100);
	for(y=0;y<H;y++)
	for(x=0;x<W;x++)
	{
		switch(view)
		{	case 0:i=y*PA*LR+x*LR+ys; break;
			case 1:i=y*PA*LR+yc*LR+x; break;
			case 2:i=ya*PA*LR+y*LR+x; break;
		}
		val=colourmap(0.5+0.5*(sum[i]/max));
		i =((H-y-1)*offcn.width+x)*4;
		px.data[ i ]  =val[0];
		px.data[ i+1 ]=val[1];
		px.data[ i+2 ]=val[2];
		px.data[ i+3 ]=255;
	}
	offtx.putImageData(px, 0, 0);
	ctx.drawImage(offcn,0,canvas.height-canvas.width*H/W,ctx.canvas.width,canvas.width*H/W);
}
function loadTemplate()
{
	var oReq = new XMLHttpRequest();
	oReq.open("GET", "/static/data/colin180.img", true);
	oReq.responseType = "arraybuffer";
	oReq.onload = function(oEvent)
	{
		template=new Uint8Array(this.response);
		//console.log("[loadTemplate] template finished loading");
		drawImages();
	};
	oReq.send();
	//console.log("[loadTemplate] template started loading");
	
}	
function loadLocations()
{
	var i;
	
	// init query volume
	for(i=0;i<LR*PA*IS;i++)
		sum[i]=0;

	// configure roi
	var	R=3;
	var	roi=new Array();
	var	nroi=0;
	for(x=-R;x<=R;x++)
	for(y=-R;y<=R;y++)
	for(z=-R;z<=R;z++)
	if(x*x+y*y+z*z<=R*R)
	{
		roi[nroi*3+0]=x;
		roi[nroi*3+1]=y;
		roi[nroi*3+2]=z;
		nroi++;
	}

	var ii,refs=[],nrefs=0;
	nLocationsLoaded=0;
	flagLocationsLoaded=0;
	var jj=refs[ii];
	$.ajax({
        type: "GET",
        url: searchString
    }).complete(function(msg) {
		exp=$.parseJSON(msg["responseText"]);
		if(exp==null) {
			console.log("ERROR: no coordinates data");
		}
		else {
			// update the sum[] volume
			var i,j,k,coord=new Array();
			exp = exp["coordinates"];
			for(i=0;i<exp.length;i++) {
				coord = exp[i].split(",");
				coord[0]=Math.floor(coord[0]/4+22);
				coord[1]=Math.floor(coord[1]/4+31);
				coord[2]=Math.floor(coord[2]/4+17.5);
				for(k=0;k<nroi;k++)
				{
					x=Math.floor(roi[k*3+0]+coord[0]);
					y=Math.floor(roi[k*3+1]+coord[1]);
					z=Math.floor(roi[k*3+2]+coord[2]);
					if(x>=0&&x<LR && y>=0&&y<PA && z>=0&&z<IS)
					{
						sum[z*PA*LR+y*LR+x]+=1;
						if(sum[z*PA*LR+y*LR+x]>max)
							max=sum[z*PA*LR+y*LR+x];
					}
				}
			}
		}

		if (exp.length > 0) {
			$("#widgetOption").text("Show widgets");
			document.getElementById("widgetOption").disabled = false;
			
			// refresh the image
			drawImages();
			updateTranslucent();
		}
		else {
			$("#widgetOption").css("display", "none");
		}
			
		/*
		if((nrefs%10)==0)
			updateTranslucent();

		// display progress
		nrefs++;
		if(nrefs==refs.length)
		{
			flagLocationsLoaded=1;

			drawImages();
			updateTranslucent();
			
			var	hdr=new Uint8Array([
92,1,0,0,100,115,114,32,32,32,32,32,32,0,82,79,73,52,109,109,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
0,0,0,0,114,48,4,0,45,0,54,0,45,0,1,0,0,0,0,0,0,0,109,109,176,0,0,0,0,0,0,0,0,0,0,0,4,0,8,
0,0,0,0,0,0,0,0,0,128,64,0,0,128,64,0,0,128,64,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,176,67,
0,224,66,69,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,255,0,0,0,0,0,0,0,103,101,110,
101,114,97,116,101,100,32,98,121,32,114,116,111,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,110,
111,110,101,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,0,0,22,0,30,0,18,0,0,
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]);
			var niiBlob = new Blob([hdr,sum]);
			$("a.download_nii").attr("href",window.URL.createObjectURL(niiBlob));
			$("a.download_nii").attr("download",searchString+".brainspell.nii"); // TODO: change
			$("a.download_nii").show();
		}
		else
			nLocationsLoaded=Math.round(100*nrefs/refs.length);
		*/
	});
}
function colourmap(val)
{
	n=191;
	i=Math.floor(val*(n-1));
	var c=[];

	c[0]=255*(negpos[    i]+(val-i/(n-1))*(negpos[    i+1]-negpos[    i]));
	c[1]=255*(negpos[  n+i]+(val-i/(n-1))*(negpos[  n+i+1]-negpos[  n+i]));
	c[2]=255*(negpos[2*n+i]+(val-i/(n-1))*(negpos[2*n+i+1]-negpos[2*n+i]));
	
	return c;
}

// Translucent Viewer
function initTranslucent()
{
	// Init render
	init_render();
	animate();

	// Add html elements
	/*
	var	dom.append("div#container");
	var info=dom.append("div#info");
	info.append("div.bottom#inlineDoc").html("[P]icture");
	info.append("input#level [type='text']").html("Isosurface level<br>");
	document.body.appendChild(dom);
	document.getElementById('level').addEventListener('change', handleLevelChange, false);
	document.getElementById("level").value = 0.06;
	*/

	// Init surface nets
	init_surfacenets();
}
function init_surfacenets()
{
	var k = 0;
	for(var i=0; i<8; ++i) {
		for(var j=1; j<=4; j<<=1) {
			var p = i^j;
			if(i <= p) {
				cube_edges[k++] = i;
				cube_edges[k++] = p;
			}
		}
	}
	for(var i=0; i<256; ++i) {
		var em = 0;
		for(var j=0; j<24; j+=2) {
			var a = !!(i & (1<<cube_edges[j]));
			var b = !!(i & (1<<cube_edges[j+1]));
			em |= a !== b ? (1 << (j >> 1)) : 0;
		}
		edge_table[i] = em;
	}
}
function SurfaceNets(data, dims, level)
{ 
	var vertices = [];
	var faces = [];
	var n = 0;
	var x = new Int32Array(3);
	var R = new Int32Array([1, (dims[0]+1), (dims[0]+1)*(dims[1]+1)]);
	var grid = new Float32Array(8);
	var buf_no = 1;

	if(R[2] * 2 > buffer.length)
		buffer = new Int32Array(R[2] * 2);

	for(x[2]=0; x[2]<dims[2]-1; ++x[2], n+=dims[0], buf_no ^= 1, R[2]=-R[2])
	{
		var m = 1 + (dims[0]+1) * (1 + buf_no * (dims[1]+1));
		for(x[1]=0; x[1]<dims[1]-1; ++x[1], ++n, m+=2)
		for(x[0]=0; x[0]<dims[0]-1; ++x[0], ++n, ++m)
		{
			var mask = 0, g = 0, idx = n;
			for(var k=0; k<2; ++k, idx += dims[0]*(dims[1]-2))
			for(var j=0; j<2; ++j, idx += dims[0]-2)      
			for(var i=0; i<2; ++i, ++g, ++idx)
			{
				var p = data[idx]-level;
				grid[g] = p;
				mask |= (p < 0) ? (1<<g) : 0;
			}
			if(mask === 0 || mask === 0xff)
				continue;
			var edge_mask = edge_table[mask];
			var v = [0.0,0.0,0.0];
			var e_count = 0;
			for(var i=0; i<12; ++i)
			{
				if(!(edge_mask & (1<<i)))
					continue;
				++e_count;
				var e0 = cube_edges[ i<<1 ];       //Unpack vertices
				var e1 = cube_edges[(i<<1)+1];
				var g0 = grid[e0];                 //Unpack grid values
				var g1 = grid[e1];
				var t  = g0 - g1;                  //Compute point of intersection
				if(Math.abs(t) > 1e-6)
					t = g0 / t;
				else
					continue;
				for(var j=0, k=1; j<3; ++j, k<<=1)
				{
					var a = e0 & k;
					var b = e1 & k;
					if(a !== b)
						v[j] += a ? 1.0 - t : t;
					else
						v[j] += a ? 1.0 : 0;
				}
			}
			var s = 1.0 / e_count;
			for(var i=0; i<3; ++i)
				v[i] = x[i] + s * v[i];
			buffer[m] = vertices.length;
			vertices.push(v);
			for(var i=0; i<3; ++i)
			{
				if(!(edge_mask & (1<<i)) )
					continue;
				var iu = (i+1)%3;
				var iv = (i+2)%3;
				if(x[iu] === 0 || x[iv] === 0)
					continue;
				var du = R[iu];
				var dv = R[iv];
				if(mask & 1)
				{
					faces.push([buffer[m], buffer[m-du-dv], buffer[m-du]]);
					faces.push([buffer[m], buffer[m-dv], buffer[m-du-dv]]);
				}
				else
				{
					faces.push([buffer[m], buffer[m-du-dv], buffer[m-dv]]);
					faces.push([buffer[m], buffer[m-du], buffer[m-du-dv]]);
				}
			}
		}
	}
	return { vertices: vertices, faces: faces };
}
function updateTranslucent()
{
	scene.remove( surfacemesh );
	scene.remove( wiremesh );

	// Configure volume
	for(i=0;i<LR*PA*IS;i++)
		volume[i]=sum[i]-max*level;
	cmap={data:volume, dims:[LR,PA,IS], level:0.5};

	//Create surface mesh
	geometry	= new THREE.Geometry();

	var start = (new Date()).getTime();
	var result = SurfaceNets(cmap.data,cmap.dims,cmap.level);
	var end = (new Date()).getTime();

	geometry.vertices.length = 0;
	geometry.faces.length = 0;

	for(var i=0; i<result.vertices.length; ++i)
	{
		var v = result.vertices[i];
		var	z=0.5;
		geometry.vertices.push(new THREE.Vector3(v[0]*z, v[1]*z, v[2]*z));
	}

	for(var i=0; i<result.faces.length; ++i) {
		var f = result.faces[i];
		if(f.length === 3) {
			geometry.faces.push(new THREE.Face3(f[0], f[1], f[2]));
		} else if(f.length === 4) {
			geometry.faces.push(new THREE.Face4(f[0], f[1], f[2], f[3]));
		} else {
			//Polygon needs to be subdivided
		}
	}

	var cb = new THREE.Vector3(), ab = new THREE.Vector3();
	cb.crossSelf=function(a){
		var b=this.x,c=this.y,d=this.z;
		this.x=c*a.z-d*a.y;
		this.y=d*a.x-b*a.z;
		this.z=b*a.y-c*a.x;
		return this;
	};
	
	for (var i=0; i<geometry.faces.length; ++i) {
		var f = geometry.faces[i];
		var vA = geometry.vertices[f.a];
		var vB = geometry.vertices[f.b];
		var vC = geometry.vertices[f.c];
		cb.subVectors(vC, vB);
		ab.subVectors(vA, vB);
		cb.crossSelf(ab);
		cb.normalize();
		f.normal.copy(cb)
	}

	geometry.verticesNeedUpdate = true;
	geometry.elementsNeedUpdate = true;
	geometry.normalsNeedUpdate = true;

	geometry.computeBoundingBox();
	geometry.computeBoundingSphere();

	var colorMaterial=new THREE.MeshBasicMaterial({color: 0xff0000, transparent: true, blending: THREE.MultiplyBlending});
	var depthMaterial=new THREE.MeshDepthMaterial({wireframe:false});
	surfacemesh = new THREE.SceneUtils.createMultiMaterialObject(geometry, [colorMaterial, depthMaterial]);
                
	surfacemesh.doubleSided=true;
	var wirematerial = new THREE.MeshBasicMaterial({
		color : 0x909090,
		wireframe : true
	});
	wiremesh = new THREE.Mesh(geometry, wirematerial);
	wiremesh.doubleSided = true;
	scene.add( surfacemesh );
	scene.add( wiremesh );

	wiremesh.position.x = surfacemesh.position.x = -cmap.dims[0]/4.0+0.5;
	wiremesh.position.y = surfacemesh.position.y = -cmap.dims[1]/4.0+0.5;
	wiremesh.position.z = surfacemesh.position.z = -cmap.dims[2]/4.0+0.5;

	surfacemesh.visible=true;
	wiremesh.visible=true;
}

function changeLevel(val)
{
	level=val/100;
	cmap.level=parseFloat(level);
	updateTranslucent();
}

// init the scene
function init_render()
{
	// Init rendered
	if( Detector.webgl ){
		renderer = new THREE.WebGLRenderer({
			antialias				: true,	// to get smoother output
			preserveDrawingBuffer	: true	// to allow screenshot
		});
		renderer.setClearColor( 0xffffff, 0 );
		renderer.setPixelRatio(window.devicePixelRatio ? window.devicePixelRatio : 1);
	}else{
		renderer = new THREE.CanvasRenderer();
	}

	var container=document.getElementById('meshCanvas');
	var	width=container.clientWidth;
	var	height=container.clientHeight;
	renderer.setSize( width, height );
	container.appendChild(renderer.domElement);

	// create a scene
	scene = new THREE.Scene();

	// put a camera in the scene
	camera	= new THREE.PerspectiveCamera(40,width/height,25,50);
	camera.position.set(0, 0, 40);
	scene.add(camera);

	// create a camera contol
	cameraControl	= new THREE.TrackballControls( camera, document.getElementById('meshCanvas') )
	cameraControl.noZoom=true;

	// allow 'p' to make screenshot
	//THREEx.Screenshot.bindKey(renderer);
	
	// configure fullscreen exit
	/*
	if (document.addEventListener)
	{
		document.addEventListener('webkitfullscreenchange', exitFullscreenHandler, false);
		document.addEventListener('mozfullscreenchange', exitFullscreenHandler, false);
		document.addEventListener('fullscreenchange', exitFullscreenHandler, false);
		document.addEventListener('MSFullscreenChange', exitFullscreenHandler, false);
	}
	*/
	
	// Add objects
	var light	= new THREE.AmbientLight( Math.random() * 0xffffff );
	scene.add( light );
	var light	= new THREE.DirectionalLight( Math.random() * 0xffffff );
	light.position.set( Math.random(), Math.random(), Math.random() ).normalize();
	scene.add( light );

	// Load mesh (ply format)
	var oReq = new XMLHttpRequest();
	oReq.open("GET", "/static/data/lrh3.ply", true);
	oReq.responseType="text";
	oReq.onload = function(oEvent)
	{
		//console.log("ply loaded");
		var tmp=this.response;
		var material;
		var geometry;
		var modifier = new THREE.SubdivisionModifier(1);
		
		material=new THREE.ShaderMaterial({
			uniforms: { 
				coeficient	: {
					type	: "f", 
					value	: 1.0
				},
				power		: {
					type	: "f",
					value	: 2
				},
				glowColor	: {
					type	: "c",
					value	: new THREE.Color('grey')
				},
			},
			vertexShader	: [ 'varying vec3	vVertexWorldPosition;',
								'varying vec3	vVertexNormal;',
								'void main(){',
								'	vVertexNormal	= normalize(normalMatrix * normal);',
								'	vVertexWorldPosition	= (modelMatrix * vec4(position, 1.0)).xyz;',
								'	gl_Position	= projectionMatrix * modelViewMatrix * vec4(position, 1.0);',
								'}',
								].join('\n'),
			fragmentShader	: [ 'uniform vec3	glowColor;',
								'uniform float	coeficient;',
								'uniform float	power;',
								'varying vec3	vVertexNormal;',
								'varying vec3	vVertexWorldPosition;',
								'void main(){',
								'	vec3 worldCameraToVertex= vVertexWorldPosition - cameraPosition;',
								'	vec3 viewCameraToVertex	= (viewMatrix * vec4(worldCameraToVertex, 0.0)).xyz;',
								'	viewCameraToVertex	= normalize(viewCameraToVertex);',
								'	float intensity		= pow(coeficient + dot(vVertexNormal, viewCameraToVertex), power);',
								'	gl_FragColor		= vec4(glowColor, intensity);',
								'}',
							].join('\n'),
			transparent	: true,
			depthWrite	: false,
		});
		
		geometry=new THREE.PLYLoader().parse(tmp);
		geometry.sourceType = "ply";
		
		//console.log("nverts",geometry.vertices.length);

		modifier.modify(geometry);
		for(i=0;i<geometry.vertices.length;i++)
		{
			geometry.vertices[i].x*=0.14;
			geometry.vertices[i].y*=0.14;
			geometry.vertices[i].z*=0.14;
			geometry.vertices[i].y+=3;
			geometry.vertices[i].z-=2;
		}

		brainmesh=new THREE.Mesh(geometry,material);
		scene.add(brainmesh);
	};
	oReq.send();
}

// animation loop
function animate()
{
	requestAnimationFrame( animate );

	render();
}

// render the scene
function render() {
	// update camera controls
	cameraControl.update();

	renderer.setClearColor( 0xffffff,1 );
	renderer.clear( true );

	// actually render the scene
	renderer.render( scene, camera );
}

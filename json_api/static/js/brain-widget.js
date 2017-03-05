function parseTable(row,eid)
{
    var ex=findExperimentByEID(eid);
    var i=-1;
    var tr=$(row).closest("tr")[0];
    if(tr)
    {
        i=$(tr).index();
        if(i>=0) {
            var cells=$(tr).find('td');
            var x=parseFloat(cells[0].textContent);
            var y=parseFloat(cells[1].textContent);
            var z=parseFloat(cells[2].textContent);
            ex.locations[i].x=x;
            ex.locations[i].y=y;
            ex.locations[i].z=z;
            
            save(eid,"locations",JSON.stringify(ex.locations,["x","y","z"]));
        }
    }
        
    // Add location spheres
    var geometry = new THREE.SphereGeometry(1,16,16);
    var color=0xff0000;
    for(j=0;j<ex.locations.length;j++)
    {
        if(ex.locations[j].sph)
        {
            color=ex.locations[j].sph.material.color;
            ex.render.spheres.remove(ex.locations[j].sph);
        }
        var x=ex.locations[j][0];
        var y=ex.locations[j][1];
        var z=ex.locations[j][2];
        var sph = new THREE.Mesh( geometry, new THREE.MeshLambertMaterial({color: color}));
        sph.position.x=parseFloat(x)*0.14;
        sph.position.y=parseFloat(y)*0.14+3;
        sph.position.z=parseFloat(z)*0.14-2;
        ex.render.spheres.add(sph);
        ex.locations[j].sph=sph;
    }
}

function updateSize() {
    var canvas=$("#3d")[0];
    var width = canvas.clientWidth;
    var height = canvas.clientHeight;
    if ( canvas.width !== width || canvas.height != height ) {
        renderer.setSize ( width, height, false );
    }
}

function animate() {
    requestAnimationFrame( animate );
    updateSize();
    renderer.setClearColor( 0xffffff,0 );
    renderer.clear( true );
    renderer.enableScissorTest( true );
    for(iExp in exp)
        if(exp[iExp].render)
            render(iExp);
    renderer.enableScissorTest( false );
}

// render the scene
function render(iExp) {
    var scene=exp[iExp].render.scene;
    var camera=exp[iExp].render.camera;
    var trackball=exp[iExp].render.cameraControls;
    
    // update camera controls
    trackball.update();
    
    // the scene object contains the element object, which is the div in which
    // 3d data is displayed.
    var element = exp[iExp].render.container[0];
    var rect = element.getBoundingClientRect();
    if ( rect.bottom < 0 || rect.top  > renderer.domElement.clientHeight ||
         rect.right  < 0 || rect.left > renderer.domElement.clientWidth ) {
      return;  // it's off screen
    }
    // set the viewport
    var width  = rect.right - rect.left;
    var height = rect.bottom - rect.top;
    var left   = rect.left;
    var bottom = renderer.domElement.clientHeight - rect.bottom;
    
    // compensate for window springiness
    var dy=window.pageYOffset;
    if(dy<0) {
        bottom-=dy;
    } else {
        dy=window.pageYOffset-document.body.scrollHeight+window.innerHeight;
        if(dy>0) {
            bottom-=dy;
        }
    }
    
    // place viewport
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setViewport( left, bottom, width, height );
    renderer.setScissor( left, bottom, width, height );
    
    // actually render the scene
    renderer.render( scene, camera );
}

// Translucent Viewer
function initTranslucentBrain(eid)
{
    var ex=findExperimentByEID(eid);
    ex.render={};
    ex.render.container=$(".experiment#"+eid+" div.metaCoords");

    var container=ex.render.container;
    var width=container.width();
    var height=container.height();
    
    // create a scene
    ex.render.scene = new THREE.Scene();
    
    // create raycaster (for hit detection)
    container[0].addEventListener( 'mousedown', function(e){onDocumentMouseDown(e,eid);}, false );

    // put a camera in the scene
    ex.render.camera    = new THREE.PerspectiveCamera(40,width/height,25,50);
    ex.render.camera.position.set(0, 0, 40);
    ex.render.scene.add(ex.render.camera);

    // create a camera control
    ex.render.cameraControls=new THREE.TrackballControls(ex.render.camera,ex.render.container[0] )
    ex.render.cameraControls.noZoom=true;
    ex.render.cameraControls.addEventListener( 'change', function(){ex.render.light.position.copy( ex.render.camera.position );} );

    // allow 'p' to make screenshot
    //THREEx.Screenshot.bindKey(renderer);
    
    // Add lights
    var light   = new THREE.AmbientLight( 0x3f3f3f);
    ex.render.scene.add(light );
    ex.render.light = new THREE.PointLight( 0xffffff,2,80 );
    //var   light   = new THREE.DirectionalLight( 0xffffff);
    //light.position.set( Math.random(), Math.random(), Math.random() ).normalize();
    ex.render.light.position.copy( ex.render.camera.position );
    //light.position.set( 0,0,0 );
    ex.render.scene.add(ex.render.light );

    // Load mesh (ply format)
    var oReq = new XMLHttpRequest();
    oReq.open("GET", "/static/data/lrh3.ply", true);
    oReq.responseType="text";
    oReq.onload = function(oEvent)
    {
        var tmp=this.response;
        var modifier = new THREE.SubdivisionModifier(1);
        
        ex.render.material=new THREE.ShaderMaterial({
            uniforms: { 
                coeficient  : {
                    type    : "f", 
                    value   : 1.0
                },
                power       : {
                    type    : "f",
                    value   : 2
                },
                glowColor   : {
                    type    : "c",
                    value   : new THREE.Color('grey')
                },
            },
            vertexShader    : [ 'varying vec3   vVertexWorldPosition;',
                                'varying vec3   vVertexNormal;',
                                'void main(){',
                                '   vVertexNormal   = normalize(normalMatrix * normal);',
                                '   vVertexWorldPosition    = (modelMatrix * vec4(position, 1.0)).xyz;',
                                '   gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);',
                                '}',
                                ].join('\n'),
            fragmentShader  : [ 'uniform vec3   glowColor;',
                                'uniform float  coeficient;',
                                'uniform float  power;',
                                'varying vec3   vVertexNormal;',
                                'varying vec3   vVertexWorldPosition;',
                                'void main(){',
                                '   vec3 worldCameraToVertex=vVertexWorldPosition - cameraPosition;',
                                '   vec3 viewCameraToVertex=(viewMatrix * vec4(worldCameraToVertex, 0.0)).xyz;',
                                '   viewCameraToVertex=normalize(viewCameraToVertex);',
                                '   float intensity=pow(coeficient + dot(vVertexNormal, viewCameraToVertex), power);',
                                '   gl_FragColor=vec4(glowColor, intensity);',
                                '}',
                            ].join('\n'),
            transparent : true,
            depthWrite  : false,
        });
        
        ex.render.geometry=new THREE.PLYLoader().parse(tmp);
        ex.render.geometry.sourceType = "ply";
        
        modifier.modify(ex.render.geometry);
        for(i=0;i<ex.render.geometry.vertices.length;i++)
        {
            ex.render.geometry.vertices[i].x*=0.14;
            ex.render.geometry.vertices[i].y*=0.14;
            ex.render.geometry.vertices[i].z*=0.14;
            ex.render.geometry.vertices[i].y+=3;
            ex.render.geometry.vertices[i].z-=2;
        }

        ex.render.brainmesh=new THREE.Mesh(ex.render.geometry,ex.render.material);
        ex.render.scene.add(ex.render.brainmesh);
    };
    oReq.send();
}

function findExperimentByEID(eid) {
    var i;
    for(i=0;i<exp.length;i++)
        if(exp[i].id==eid)
            break;
    if(i==exp.length) {
        console.log("ERROR: eid "+eid+" not found!");
    }
    return exp[i];
}

function addExperiment(eid)
{
    return function(responseText, textStatus, XMLHttpRequest){

        // Configure legend (title and caption)
        //-------------------------------------
        var ex = findExperimentByEID(eid);
        var title=(ex.title)?ex.title:"";
        var caption=(ex.caption)?ex.caption:"";
        $(".experiment#"+eid+" .title").append(title);
        $(".experiment#"+eid+" .caption").append(caption);

        // Configure locations to 3D view
        //-------------------------------
        initTranslucentBrain(eid);
        ex.render.spheres = new THREE.Object3D();
        ex.render.scene.add(ex.render.spheres);

        // Configure stereotaxic table
        //----------------------------
        var table=$(".experiment#"+eid+" .xyztable table");
        if(table==undefined)
            console.log("ERROR: table undefined");
        table.click(function(e){if(e.target.tagName=="TD") clickOnTable(e.target)});
        table.keydown(function(e){keydownOnTable(e.target)});

        // Add experiment locations to table
        if(!ex.locations)
            return;
        var html="";
        table=$(".experiment#"+eid+" .xyztable table")[0];
        for(j=0;j<ex.locations.length;j++)
        {
            var coords=[];
            if(typeof ex.locations[j] == "string") {
                coords=ex.locations[j].split(",");
                ex.locations[j]={
                    x:coords[0],
                    y:coords[1],
                    z:coords[2]
                }
            } else {
                coords[0]=ex.locations[j][0];
                coords[1]=ex.locations[j][1];
                coords[2]=ex.locations[j][2];
            }
            var new_row = table.insertRow(j);
            new_row.innerHTML=[
                "<td class='coordinate'>"+coords[0]+"</td>",
                "<td class='coordinate'>"+coords[1]+"</td>",
                "<td class='coordinate'>"+coords[2]+"</td>",
                "<td class='input'><input type='image' class='del' src='/static/img/minus-circle.svg' onclick='delRow(this)'/></td>",
                "<td class='input'><input type='image' class='add' src='/static/img/plus-circle.svg' onclick='addRow(this)'/></td>"
            ].join("\n");
        }

        // Intercept enter on table cells
        $(".experiment#"+eid+" .xyztable table td").on( 'keydown',function(e) {
            if(e.which==13&&e.shiftKey==false) {    // enter (without shift)
                parseTable(this,eid);
                return false;
            }
            if(e.which==9) {    // tab
                parseTable(this,eid);
            }
        });
        
        // Table actions
        //--------------
        // Split table
        $(".experiment#"+eid+" .button.split").click(function() {
            splitTable(eid,ex.selectedRow);
        });
        // Import table
        $(".experiment#"+eid+" .button.import").click(function() {
            importTable(eid);
        });

        // Parse locations: add locations to
        // 3d view and to stereotaxic table
        //----------------------------------
        parseTable("",eid);
        
        // Configure radio button groups for table marks
        $(".experiment#"+eid+" input:radio[value='Yes']").attr('name',"radio"+eid);
        $(".experiment#"+eid+" input:radio[value='No']").attr('name',"radio"+eid);

        updateExperiment(eid);
    }
}

function onDocumentMouseDown( event,eid ) {
    event.preventDefault();
    var ex=findExperimentByEID(eid);
    var x,y,i;
    var r = event.target.getBoundingClientRect();

    mouseVector = new THREE.Vector3();
    mouseVector.x= ((event.clientX-r.left) / event.target.clientWidth ) * 2 - 1;
    mouseVector.y=-((event.clientY-r.top) / event.target.clientHeight ) * 2 + 1;
    
    var raycaster=new THREE.Raycaster();
    raycaster.setFromCamera(mouseVector.clone(), ex.render.camera);
    var intersects = raycaster.intersectObjects( ex.render.spheres.children );

    if(intersects.length==0)
        return;
    ex.render.spheres.children.forEach(function( sph ) { sph.material.color.setRGB( 1,0,0 );});
    intersects[0].object.material.color.setRGB(0,1,0);
    $(".experiment#"+eid+" .xyztable table td").css({'background-color':''});
    for(i=0;i<ex.locations.length;i++)
        if(ex.locations[i].sph==intersects[0].object)
            $(".experiment#"+eid+" .xyztable tr:eq("+i+") td.coordinate").css({"background-color":"lightGreen"});
}

function updateExperiment(eid)
{
    
    /*
        Experiment-level display
        ------------------------
    */
    $(".stored").removeAttr('contentEditable');
    $(".experiment#"+eid+" .stored").removeClass('stored');

    // Experiment table mark (global)
    $(".experiment#"+eid+" div.tableAlert").show();
    $(".experiment#"+eid+" div.tableMark").hide();
    $(".experiment#"+eid+" td.coordinate").removeAttr("contentEditable");
    $(".experiment#"+eid+" th.input").hide();
    $(".experiment#"+eid+" td.input").hide();
    $(".experiment#"+eid+" .tableActions").hide();
    
    // Adjust locations table height
    var padd,legendheight,xyzhdrheight,ontheight,tableActionsHeight;
    padd=parseInt($('.experiment#'+eid).css('padding-top'));
    legendheight=$('.experiment#'+eid+' .experiment-title').innerHeight();
    legendheight+=$('.experiment#'+eid+' .experiment-caption').innerHeight();
    xyzhdrheight=$('.experiment#'+eid+' .xyzheader').innerHeight();
    ontheight=$('.experiment#'+eid+' .ontologies').innerHeight();
    badTableHeight=$(".experiment#"+eid+" input.badTable").innerHeight()+10;
    tableActionsHeight=0;
    $('.experiment#'+eid+' .xyztable').css({"height":300,"max-height":300-badTableHeight-padd-tableActionsHeight});
}
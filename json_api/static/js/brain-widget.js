function animate() {
    // animation loop
    // update size, if changed
    var canvas=$("#3d")[0];
    var width = canvas.clientWidth;
    var height = canvas.clientHeight;
    if (canvas.width !== width || canvas.height != height) {
        renderer.setSize ( width, height, false );
    }
    // render
    renderer.setClearColor(0xffffff, 0);
    renderer.clear(true);
    renderer.enableScissorTest(true);
    for (i in exp) {
        if(exp[i].render) {
            render(exp[i]);
        }
    }
    renderer.enableScissorTest(false);
    requestAnimationFrame(animate);
}

// render the scene; called by animation loop
function render(experiment) {
    var scene = experiment.render.scene;
    var camera = experiment.render.camera;
    var trackball = experiment.render.cameraControls;

    // update camera controls
    trackball.update();

    // the scene object contains the element object, which is the div in which
    // 3d data is displayed.
    var element = experiment.render.container[0];
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

    renderer.render(scene, camera);
}

// INITIAL RENDERING

// call when the brain template is loaded
function addExperiment(eid, experiment) {
    // add title/caption
    var title=(experiment.title)?experiment.title:"";
    var caption=(experiment.caption)?experiment.caption:"";
    $(".experiment#"+eid+" .title").append(title);
    $(".experiment#"+eid+" .caption").append(caption);

    // Configure locations to 3D view
    initTranslucentBrain(eid, experiment);
    experiment.render.spheres = new THREE.Object3D();
    experiment.render.scene.add(experiment.render.spheres);

    // Parse locations: add locations to 3d view and to stereotaxic table
    if(experiment.locations) {
        parseLocations(eid, experiment);
    }
}

function initTranslucentBrain(eid, ex)
{
    ex.render={};
    ex.render.container=$(".experiment#"+eid+" div.metaCoords");

    var container=ex.render.container;
    var width=container.width();
    var height=container.height();

    // create a scene
    ex.render.scene = new THREE.Scene();

    // create raycaster (for hit detection)
    container[0].addEventListener('mousedown', function(e){onDocumentMouseDown(e, eid, ex);}, false);

    // put a camera in the scene
    ex.render.camera    = new THREE.PerspectiveCamera(40,width/height,25,50);
    ex.render.camera.position.set(0, 0, 40);
    ex.render.scene.add(ex.render.camera);

    // create a camera control
    ex.render.cameraControls=new THREE.TrackballControls(ex.render.camera,ex.render.container[0])
    ex.render.cameraControls.noZoom=true;
    ex.render.cameraControls.addEventListener('change', function(){ex.render.light.position.copy( ex.render.camera.position );});

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

function parseLocations(eid, ex)
{
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

// handle clicking on location spheres
function onDocumentMouseDown(event, eid, ex) {
    event.preventDefault();
    var r = event.target.getBoundingClientRect();

    mouseVector = new THREE.Vector3();
    mouseVector.x= ((event.clientX-r.left) / event.target.clientWidth ) * 2 - 1;
    mouseVector.y=-((event.clientY-r.top) / event.target.clientHeight ) * 2 + 1;

    var raycaster=new THREE.Raycaster();
    raycaster.setFromCamera(mouseVector.clone(), ex.render.camera);
    var intersects = raycaster.intersectObjects( ex.render.spheres.children );

    if(intersects.length==0)
        return;
    ex.render.spheres.children.forEach(function(sph) { sph.material.color.setRGB( 1,0,0 );});
    intersects[0].object.material.color.setRGB(0,1,0);
    $("#container"+eid+" table tbody .experiment-table-row").css({'background-color':'#e8edff'});
    for(var i=0;i<ex.locations.length;i++){
        if(ex.locations[i].sph==intersects[0].object) {
            console.log("clicked row", i)
            console.log("guess page", Math.floor((i+1)/7)+1)
            clickedRow = $("#container"+eid+" table tbody .experiment-table-row:eq("+i+")");
            /*$("#container"+eid+" table tbody .experiment-table-row:eq("+i+")").css({"background-color":"lightGreen"});
            $("#container"+eid+" table .experiments-tbody").scrollTop($("#container"+eid+" table .experiments-tbody").scrollTop()
                + clickedRow.position().top - clickedRow.height());*/
        }
    }
}

function rowClicked(row, element) {
    var ex = exp[element];
    var i = $(row).index() - 1;
    //$("#container"+ex.id+" table tbody .experiment-table-row").css({'background-color':'#e8edff'});

    ex.render.spheres.children.forEach(function( sph ) { sph.material.color.setRGB( 1,0,0 );});

    if(i >= 0) {
        $(row).css({'background-color':'lightGreen'});
        ex.locations[i].sph.material.color.setRGB(0,1,0);
        ex.selectedRow=i;
    }
}

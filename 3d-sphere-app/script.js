// Set up scene, camera, renderer
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.getElementById('scene').appendChild(renderer.domElement);

// Create sphere
const geometry = new THREE.SphereGeometry(1, 64, 64);
const material = new THREE.MeshStandardMaterial({
    color: 0x00ff00,
    emissive: 0x004400,
    emissiveIntensity: 0.3,
    roughness: 0.5,
    metalness: 0.1
});
const sphere = new THREE.Mesh(geometry, material);
scene.add(sphere);

// Add light for better glow
const light = new THREE.PointLight(0xffffff, 1, 100);
light.position.set(10, 10, 10);
scene.add(light);

// Camera position
camera.position.z = 5;

// Mouse interaction
let mouse = { x: 0, y: 0 };
document.addEventListener('mousemove', (event) => {
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
});

// Animation loop
function animate() {
    requestAnimationFrame(animate);
    // Spinning
    sphere.rotation.x += 0.005;
    sphere.rotation.y += 0.005;
    // Respond to mouse
    sphere.rotation.x += mouse.y * 0.01;
    sphere.rotation.y += mouse.x * 0.01;
    renderer.render(scene, camera);
}
animate();

// Handle window resize
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});
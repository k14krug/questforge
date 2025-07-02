// Three.js Dice Roller
// Creates realistic 3D dice rolling animations


// Dice roller class
export default class DiceRoller {
    constructor(container) {
        this.container = container;
        this.diceValues = [];
        this.targetValue = null;  // Added for server-driven rolls
        this.init();
    }

    init() {
        // Scene setup
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0xf0f0f0);

        // Camera setup
        this.camera = new THREE.PerspectiveCamera(75, this.container.clientWidth / this.container.clientHeight, 0.1, 1000);
        this.camera.position.z = 15;
        this.camera.position.y = 8;

        // Renderer setup
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.container.appendChild(this.renderer.domElement);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10, 20, 15);
        this.scene.add(directionalLight);

        // Controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;

        // Create dice
        this.createDice();

        // Animation loop
        this.animate();
    }

    createDice() {
        // Dice material
        const diceMaterial = new THREE.MeshPhongMaterial({
            color: 0xff0000,
            shininess: 60,
            specular: 0xffffff
        });

        // Create dice geometry
        const diceGeometry = new THREE.BoxGeometry(3, 3, 3);
        this.dice = new THREE.Mesh(diceGeometry, diceMaterial);
        this.scene.add(this.dice);

        // Add dice dots
        const dotMaterial = new THREE.MeshPhongMaterial({ color: 0xffffff });
        const dotGeometry = new THREE.SphereGeometry(0.4, 16, 16);
        
        // Positions for dice dots (standard die pattern)
        const dotPositions = [
            [0, 0, 1.51], [0, 0, -1.51], // Front and back
            [0, 1.51, 0], [0, -1.51, 0],  // Top and bottom
            [1.51, 0, 0], [-1.51, 0, 0]   // Right and left
        ];

        dotPositions.forEach(pos => {
            const dot = new THREE.Mesh(dotGeometry, dotMaterial);
            dot.position.set(pos[0], pos[1], pos[2]);
            this.dice.add(dot);
        });

        // Physics properties
        this.velocity = new THREE.Vector3(
            (Math.random() - 0.5) * 10,
            (Math.random() - 0.5) * 10,
            (Math.random() - 0.5) * 10
        );
        
        this.angularVelocity = new THREE.Vector3(
            (Math.random() - 0.5) * 0.5,
            (Math.random() - 0.5) * 0.5,
            (Math.random() - 0.5) * 0.5
        );
    }

    // Roll the dice to a specific value (server-driven)
    rollToValue(targetValue, diceType = 'd20') {
        this.targetValue = targetValue;
        this.rolling = true;
        
        // Reset dice position
        this.dice.position.set(0, 0, 0);
        this.dice.rotation.set(0, 0, 0);
        
        // Calculate physics for target value
        const angleMap = {
            'd20': this.calculateD20Angles()
        };
        
        const angles = angleMap[diceType] || this.calculateD20Angles();
        this.angularVelocity.set(angles.x, angles.y, angles.z);
        
        setTimeout(() => {
            this.rolling = false;
            this.calculateResult();
        }, 2000);
    }

    // Calculate physics for d20 to land on target value
    calculateD20Angles() {
        const rotations = {
            1: { x: 0, y: 0, z: 0 },
            20: { x: Math.PI, y: 0, z: 0 }
            // Add more mappings as needed
        };
        
        return rotations[this.targetValue] || {
            x: (Math.random() - 0.5) * 1,
            y: (Math.random() - 0.5) * 1,
            z: (Math.random() - 0.5) * 1
        };
    }

    // Roll the dice with random animation
    rollDice() {
        // Reset physics
        this.velocity.set(
            (Math.random() - 0.5) * 20,
            (Math.random() - 0.5) * 20,
            (Math.random() - 0.5) * 20
        );
        
        this.angularVelocity.set(
            (Math.random() - 0.5) * 1,
            (Math.random() - 0.5) * 1,
            (Math.random() - 0.5) * 1
        );

        // Reset dice position
        this.dice.position.set(0, 0, 0);
        this.dice.rotation.set(0, 0, 0);

        // Start rolling animation
        this.rolling = true;
        setTimeout(() => {
            this.rolling = false;
            this.calculateResult();
        }, 3000);
    }

    calculateResult() {
        // Use target value if set (server-driven roll)
        if (this.targetValue !== null) {
            this.diceValues = [this.targetValue];
            this.targetValue = null;  // Reset for next roll
            return;
        }

        // Fallback to random calculation
        const value = Math.floor(Math.random() * 6) + 1;
        this.diceValues = [value];
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        if (this.rolling) {
            // Apply physics
            this.dice.position.add(this.velocity);
            this.dice.rotation.x += this.angularVelocity.x;
            this.dice.rotation.y += this.angularVelocity.y;
            this.dice.rotation.z += this.angularVelocity.z;

            // Simple floor collision
            if (this.dice.position.y < -5) {
                this.dice.position.y = -5;
                this.velocity.y *= -0.8;
            }

            // Damping
            this.velocity.multiplyScalar(0.99);
            this.angularVelocity.multiplyScalar(0.97);
        }

        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }

    resize() {
        this.camera.aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
    }
}

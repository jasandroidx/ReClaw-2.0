### PART 1: THE FILENAME ROADMAP

#### 1\. Procedural Asset Engine: scripts/generate\_assets.py

This script utilizes Python Pillow to generate 48x48 pixel-perfect environment tiles cite: 9, 20\. It enforces zero anti-aliasing and strict hex-palette conformity for modular injection into the Phaser 3 dashboard cite: 1, 20\.  
**Server Path:** /root/ReClaw-2.0/scripts/generate\_assets.py cite: 20  
from PIL import Image, ImageDraw

\# Strict Hex Palette (RGBA) \[cite: 10, 20\]  
PALETTE \= {  
    "STONE": (42, 31, 53, 255),    \# \#2a1f35  
    "NEON": (255, 0, 204, 255),     \# \#ff00cc  
    "GLOW": (0, 255, 204, 255),     \# \#00ffcc  
    "TOOL": (201, 162, 39, 255),    \# \#c9a227  
    "HOT": (255, 238, 136, 255),    \# \#ffee88  
    "WARM": (255, 136, 0, 255\)      \# \#ff8800  
}

def generate\_tile(filename, draw\_func):  
    \# 48x48 resolution \[cite: 9\]  
    img \= Image.new("RGBA", (48, 48), (0, 0, 0, 0))   
    draw \= ImageDraw.Draw(img)  
    draw\_func(draw)  
    img.save(f"/root/ReClaw-2.0/dashboard/public/assets/{filename}.png") \[cite: 20\]

def draw\_stone\_floor(draw):  
    draw.rectangle(\[1\], fill=PALETTE\["STONE"\]) \# Base stone \[cite: 10\]

def draw\_wall\_border(draw):  
    \# Double purple conduit with energy core \[cite: 20\]  
    draw.rectangle(\[1-3\], fill=PALETTE\["NEON"\])  
    draw.rectangle(\[1, 4, 5\], fill=PALETTE\["GLOW"\])

def draw\_ui\_panel(draw):  
    \# Double-inset beveled frame \[cite: 20\]  
    draw.rectangle(\[6, 7\], outline=PALETTE\["TOOL"\], width=2)

#### 2\. Native Canvas UI Console: dashboard/src/ScrollableConsole.ts

To eliminate GPU context-switching and layout reflow penalties associated with DOM overlays, this class implements a pure native Phaser 3 UI using container hierarchies and geometry masking cite: 6, 20\.  
**Server Path:** /root/ReClaw-2.0/dashboard/src/ScrollableConsole.ts cite: 20  
import \* as Phaser from 'phaser';

export class ScrollableConsole extends Phaser.GameObjects.Container {  
    private content: Phaser.GameObjects.Container;  
    private maskShape: Phaser.GameObjects.Graphics;

    constructor(scene: Phaser.Scene, x: number, y: number) {  
        super(scene, x, y);  
        this.content \= scene.add.container(0, 0);  
        this.add(this.content);

        // Apply GeometryMask to prevent coordinate leakage \[cite: 20\]  
        this.maskShape \= scene.make.graphics({ x, y, add: false });  
        this.maskShape.fillRect(0, 0, 400, 300);  
        this.setMask(new Phaser.Display.Masks.GeometryMask(scene, this.maskShape));

        // Precision configuration \[cite: 20\]  
        this.scene.game.config.roundPixels \= true;  
    }

    public appendLog(text: string): void {  
        const entry \= this.scene.add.text(10, this.content.length \* 20, text, {  
            fontFamily: 'monospace',  
            fontSize: '14px',  
            color: '\#00ffcc' // Glow color \[cite: 10\]  
        });  
        entry.setResolution(window.devicePixelRatio); // High-DPI crispness \[cite: 20\]  
        this.content.add(entry);  
    }  
}

#### 3\. High-Performance Particle Matrix: dashboard/src/ClawforgeEmitter.ts

The anvil spark emitter uses GPU-driven batching to visualize task compilation and execution via forge sparks cite: 10, 20\. It maps white-hot hotspots to thermal orange dissipation using linear RGB interpolation cite: 20\.  
**Server Path:** /root/ReClaw-2.0/dashboard/src/ClawforgeEmitter.ts cite: 20  
export function createClawforgeEmitter(scene: Phaser.Scene, x: number, y: number) {  
    return scene.add.particles(x, y, 'procedural\_spark', {  
        lifespan: { min: 400, max: 800 }, \[cite: 20\]  
        speed: { min: 200, max: 400 },  
        angle: { min: 240, max: 300 }, // Radial spray upward \[cite: 20\]  
        gravityY: 600,  
        scale: { start: 1.0, end: 0.1 },  
        alpha: { start: 1.0, end: 0.0 },  
        blendMode: 'ADD', // Glowing overlay effect \[cite: 20\]  
        tint: \[0xffee88, 0xff8800\] // Forge Sparks: Hot to Low \[cite: 10, 20\]  
    });  
}

### PART 2: THE BULLETPROOFING FAQ

**1\. Network Disconnection: How does the Phaser 3 frontend handle a sudden drop or heartbeat loss from the Python WebSocket gateway on port 18789 without crashing the game loop?**The frontend utilizes a standalone RavenstackWSClient that decouples network synchronization from the primary rendering lifecycle to prevent stuttering cite: 20\. It maintains a 30-second probe interval and a state machine that handles error backoff with jitter cite: 20\. Visual indicators, such as the WebSocket status aura (\#00ffcc), transition to a "frozen" or inactive state in the display list if the heartbeat epoch verification identifies delayed or missing packets cite: 10, 20\.  
**2\. Boundary Violations: How does the coordinate parser handle invalid or out-of-bounds grid positions pushed by automated agent loops?**The system uses a spatial proximity validation matrix cite: 20\. Incoming JSON state deltas from castle\_map.json are filtered against trigger coordinates and physics engine AABB overlap queries cite: 20, 712\. If an agent's coordinate translation attempts to move outside its assigned modular room boundaries—such as the 48x48 operational grid—the RavenstackWSClient freezes translation and triggers an floating text fault notification (+FAULT) using the Neon-Purple (\#ff00cc) outline cite: 10, 20\.  
**3\. File Contention: How does the backend prevent concurrent file-write corruption when multiple 24/7 agents finish tasks at the exact same millisecond?**ReClaw-2.0 prevents context disintegration by anchoring state durability to localized, isolated memory architectures for each agent room cite: 1, 13\. Clawsmith (core/cell.py) acts as the gatekeeper, executing a preliminary auditing and classification sequence cite: 11, 12\. All task completions are serialized into "Durable Task Objects" tracked via a centralized JSON ledger (castle\_map.json) cite: 18\. The system utilizes a WebSocket execution lock; any action impacting external directories is flagged for manual operator review in the Evidence Panel before the backend release is authorized cite: 18, 19\. Additionally, automated consolidation tasks run every 6 hours to deduplicate redundant entries with a cosine similarity ≥ 0.95, ensuring database integrity cite: 14, 15\.  

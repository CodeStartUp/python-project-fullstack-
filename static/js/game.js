// Flappy Bird Game - Fixed with proper pipe distance
class FlappyBirdGame {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        
        // Game dimensions
        this.width = 400;
        this.height = 600;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
        
        // Bird properties
        this.bird = {
            x: 80,
            y: this.height / 2,
            width: 34,
            height: 24,
            velocity: 0,
            gravity: 0.22,
            jump: -5.2,
            rotation: 0,
            maxVelocity: 7
        };
        
        // Pipe properties - FIXED: 2.5 meters distance (250px)
        this.pipes = [];
        this.pipeWidth = 55;
        this.pipeGap = 180;      // Starting gap
        this.minPipeGap = 150;    // Minimum gap
        this.pipeSpacing = 250;   // 2.5 METERS distance between pipes!
        this.basePipeSpeed = 1.5;
        this.currentPipeSpeed = 1.5;
        
        // Difficulty settings
        this.score = 0;
        this.level = 1;
        this.pipesPassed = 0;
        this.gameplayData = [];
        this.startTime = Date.now();
        
        // Game state
        this.gameRunning = false;
        this.gameOver = false;
        
        // Colors
        this.pipeColor = '#DC5539';
        this.pipeBorderColor = '#B84C39';
        
        // Assets
        this.background = null;
        this.birdImage = null;
        
        this.loadAssets();
        this.init();
    }
    
    loadAssets() {
        this.background = new Image();
        this.background.src = '/static/bg.png';
        this.background.onerror = () => {
            this.background = null;
        };
        
        this.birdImage = new Image();
        this.birdImage.src = '/static/bird.png';
        this.birdImage.onerror = () => {
            this.birdImage = null;
        };
    }
    
    init() {
        this.gameRunning = true;
        this.gameOver = false;
        this.score = 0;
        this.level = 1;
        this.pipesPassed = 0;
        this.currentPipeSpeed = this.basePipeSpeed;
        this.pipeGap = 180;
        this.bird.y = this.height / 2;
        this.bird.velocity = 0;
        this.bird.rotation = 0;
        this.pipes = [];
        this.gameplayData = [];
        this.startTime = Date.now();
        
        // Create first pipe after delay
        setTimeout(() => {
            if (this.gameRunning) {
                this.createPipe();
            }
        }, 1000);
        
        // Event listeners
        this.handleInput = this.handleInput.bind(this);
        document.addEventListener('keydown', this.handleInput);
        this.canvas.addEventListener('click', () => this.jump());
        this.canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this.jump();
        });
        
        // Start game loop
        this.gameLoop();
    }
    
    createPipe() {
        let topHeight;
        let isValid = false;
        let attempts = 0;
        
        const minTopHeight = 60;
        const maxTopHeight = this.height - this.pipeGap - 60;
        
        while (!isValid && attempts < 30) {
            topHeight = Math.floor(Math.random() * (maxTopHeight - minTopHeight + 1) + minTopHeight);
            isValid = true;
            
            // Check against existing pipes
            for (let pipe of this.pipes) {
                const horizontalDistance = Math.abs((this.width + 50) - pipe.x);
                
                // FIXED: Ensure exactly 250px distance (2.5 meters)
                if (horizontalDistance < this.pipeSpacing) {
                    isValid = false;
                    break;
                }
                
                // Ensure gaps are within reasonable vertical distance
                const verticalDistance = Math.abs(topHeight - pipe.topHeight);
                if (verticalDistance > 100) {
                    isValid = false;
                    break;
                }
            }
            attempts++;
        }
        
        this.pipes.push({
            x: this.width,
            topHeight: topHeight,
            bottomY: topHeight + this.pipeGap,
            width: this.pipeWidth,
            passed: false,
            createdAt: Date.now()
        });
    }
    
    jump() {
        if (this.gameRunning && !this.gameOver) {
            this.bird.velocity = this.bird.jump;
            this.bird.rotation = -0.4;
            
            if (window.navigator.vibrate) {
                window.navigator.vibrate(30);
            }
        } else if (this.gameOver) {
            this.saveGameplayData();
            this.resetGame();
        }
    }
    
    handleInput(e) {
        if (e.code === 'Space' || e.code === 'ArrowUp') {
            e.preventDefault();
            this.jump();
        }
    }
    
    updateDifficulty() {
        // Update level every 40 points
        this.level = Math.floor(this.score / 40) + 1;
        
        // Increase speed based on level (capped)
        this.currentPipeSpeed = Math.min(this.basePipeSpeed + (this.level - 1) * 0.15, 3.5);
        
        // Decrease pipe gap slowly
        this.pipeGap = Math.max(this.minPipeGap, 180 - (this.level - 1) * 2);
        
        // Record gameplay data
        if (this.score % 10 === 0 && this.gameplayData.length < 100 && this.score > 0) {
            this.gameplayData.push({
                score: this.score,
                level: this.level,
                speed: this.currentPipeSpeed,
                time: (Date.now() - this.startTime) / 1000,
                gap: this.pipeGap
            });
        }
    }
    
    update() {
        if (!this.gameRunning || this.gameOver) return;
        
        this.updateDifficulty();
        
        // Bird physics
        this.bird.velocity += this.bird.gravity;
        if (this.bird.velocity > this.bird.maxVelocity) {
            this.bird.velocity = this.bird.maxVelocity;
        }
        this.bird.y += this.bird.velocity;
        this.bird.rotation = Math.min(Math.max(this.bird.velocity * 0.08, -0.6), 0.6);
        
        // Bird boundaries
        if (this.bird.y + this.bird.height >= this.height) {
            this.bird.y = this.height - this.bird.height;
            this.gameOver = true;
            this.gameRunning = false;
            this.saveScore();
            this.saveGameplayData();
        }
        
        if (this.bird.y <= 0) {
            this.bird.y = 0;
            this.gameOver = true;
            this.gameRunning = false;
            this.saveScore();
            this.saveGameplayData();
        }
        
        // Update pipes and collisions
        for (let i = 0; i < this.pipes.length; i++) {
            this.pipes[i].x -= this.currentPipeSpeed;
            
            // Collision detection
            const birdLeft = this.bird.x;
            const birdRight = this.bird.x + this.bird.width;
            const pipeLeft = this.pipes[i].x;
            const pipeRight = this.pipes[i].x + this.pipeWidth;
            
            if (birdRight > pipeLeft && birdLeft < pipeRight) {
                if (this.bird.y < this.pipes[i].topHeight ||
                    this.bird.y + this.bird.height > this.pipes[i].bottomY) {
                    this.gameOver = true;
                    this.gameRunning = false;
                    this.saveScore();
                    this.saveGameplayData();
                }
            }
            
            // Score points
            if (!this.pipes[i].passed && this.pipes[i].x + this.pipeWidth < this.bird.x) {
                this.pipes[i].passed = true;
                this.score += 10;
                this.pipesPassed++;
                this.updateScore();
                this.playScoreSound();
            }
        }
        
        // Remove offscreen pipes
        this.pipes = this.pipes.filter(pipe => pipe.x + this.pipeWidth > 0);
        
        // Spawn new pipes with EXACT spacing
        if (this.pipes.length === 0) {
            this.createPipe();
        } else {
            const lastPipe = this.pipes[this.pipes.length - 1];
            // Spawn when last pipe is exactly at spacing distance
            if (lastPipe.x <= this.width - this.pipeSpacing) {
                this.createPipe();
            }
        }
    }
    
    playScoreSound() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.value = 880;
            gainNode.gain.value = 0.08;
            
            oscillator.start();
            gainNode.gain.exponentialRampToValueAtTime(0.00001, audioContext.currentTime + 0.08);
            oscillator.stop(audioContext.currentTime + 0.08);
        } catch(e) {}
    }
    
    async saveScore() {
        try {
            const response = await fetch('/api/update-score', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ score: this.score })
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Score saved:', data);
            }
        } catch(err) {
            console.error('Error saving score:', err);
        }
    }
    
    async saveGameplayData() {
        try {
            const response = await fetch('/api/save-gameplay', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    gameplayData: this.gameplayData,
                    finalScore: this.score,
                    finalLevel: this.level,
                    pipesPassed: this.pipesPassed
                })
            });
        } catch(err) {
            console.error('Error saving gameplay data:', err);
        }
    }
    
    drawBackground() {
        if (this.background && this.background.complete && this.background.naturalWidth > 0) {
            this.ctx.drawImage(this.background, 0, 0, this.width, this.height);
        } else {
            const gradient = this.ctx.createLinearGradient(0, 0, 0, this.height);
            gradient.addColorStop(0, '#4EC0CA');
            gradient.addColorStop(0.5, '#88DED1');
            gradient.addColorStop(1, '#FFE6B0');
            this.ctx.fillStyle = gradient;
            this.ctx.fillRect(0, 0, this.width, this.height);
            
            this.drawCloud(50, 80, 60);
            this.drawCloud(250, 120, 50);
            this.drawCloud(150, 200, 70);
            this.drawCloud(320, 300, 55);
            this.drawCloud(30, 400, 65);
        }
    }
    
    drawCloud(x, y, size) {
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
        this.ctx.beginPath();
        this.ctx.arc(x, y, size * 0.5, 0, Math.PI * 2);
        this.ctx.arc(x + size * 0.4, y - size * 0.2, size * 0.4, 0, Math.PI * 2);
        this.ctx.arc(x - size * 0.3, y - size * 0.1, size * 0.4, 0, Math.PI * 2);
        this.ctx.fill();
    }
    
    drawBird() {
        this.ctx.save();
        this.ctx.translate(this.bird.x + this.bird.width/2, this.bird.y + this.bird.height/2);
        this.ctx.rotate(this.bird.rotation);
        
        if (this.birdImage && this.birdImage.complete && this.birdImage.naturalWidth > 0) {
            this.ctx.drawImage(this.birdImage, -this.bird.width/2, -this.bird.height/2, 
                              this.bird.width, this.bird.height);
        } else {
            this.ctx.fillStyle = '#FFD700';
            this.ctx.fillRect(-this.bird.width/2, -this.bird.height/2, this.bird.width, this.bird.height);
            
            this.ctx.fillStyle = 'white';
            this.ctx.beginPath();
            this.ctx.arc(this.bird.width/4, -this.bird.height/6, 5, 0, Math.PI * 2);
            this.ctx.fill();
            
            this.ctx.fillStyle = 'black';
            this.ctx.beginPath();
            this.ctx.arc(this.bird.width/4 + 2, -this.bird.height/6, 2, 0, Math.PI * 2);
            this.ctx.fill();
            
            this.ctx.fillStyle = '#FFA500';
            this.ctx.beginPath();
            this.ctx.moveTo(this.bird.width/2, -this.bird.height/6);
            this.ctx.lineTo(this.bird.width/2 + 8, -this.bird.height/6);
            this.ctx.lineTo(this.bird.width/2, -this.bird.height/12);
            this.ctx.fill();
        }
        
        this.ctx.restore();
    }
    
    drawPipes() {
        for (const pipe of this.pipes) {
            // Draw distance indicator
            this.ctx.fillStyle = 'rgba(0, 255, 0, 0.15)';
            this.ctx.fillRect(pipe.x, pipe.topHeight, pipe.width, this.pipeGap);
            
            // Draw distance text
            this.ctx.fillStyle = 'white';
            this.ctx.font = 'bold 10px Arial';
            this.ctx.shadowBlur = 0;
            this.ctx.fillText('2.5m', pipe.x + 10, pipe.topHeight - 10);
            
            // Top pipe
            const topGradient = this.ctx.createLinearGradient(pipe.x, 0, pipe.x + pipe.width, 0);
            topGradient.addColorStop(0, this.pipeColor);
            topGradient.addColorStop(1, this.pipeBorderColor);
            this.ctx.fillStyle = topGradient;
            this.ctx.fillRect(pipe.x, 0, pipe.width, pipe.topHeight);
            
            this.ctx.fillStyle = this.pipeBorderColor;
            this.ctx.fillRect(pipe.x - 5, pipe.topHeight - 30, pipe.width + 10, 30);
            
            // Bottom pipe
            const bottomGradient = this.ctx.createLinearGradient(pipe.x, 0, pipe.x + pipe.width, 0);
            bottomGradient.addColorStop(0, this.pipeColor);
            bottomGradient.addColorStop(1, this.pipeBorderColor);
            this.ctx.fillStyle = bottomGradient;
            this.ctx.fillRect(pipe.x, pipe.bottomY, pipe.width, this.height - pipe.bottomY);
            
            this.ctx.fillStyle = this.pipeBorderColor;
            this.ctx.fillRect(pipe.x - 5, pipe.bottomY, pipe.width + 10, 30);
        }
    }
    
    drawScore() {
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
        this.ctx.fillRect(this.width/2 - 60, 10, 120, 80);
        
        this.ctx.fillStyle = 'white';
        this.ctx.font = 'bold 32px "Arial", "Courier New", monospace';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(this.score, this.width/2, 50);
        
        this.ctx.font = 'bold 14px "Arial", "Courier New", monospace';
        this.ctx.fillStyle = '#FFD700';
        this.ctx.fillText(`Level ${this.level}`, this.width/2, 28);
        
        this.ctx.font = '10px "Arial", "Courier New", monospace';
        this.ctx.fillStyle = 'rgba(255,255,255,0.7)';
        this.ctx.fillText(`Distance: 2.5m`, this.width/2, 85);
        
        this.ctx.textAlign = 'left';
    }
    
    drawGameOver() {
        if (this.gameOver) {
            this.ctx.fillStyle = 'rgba(0, 0, 0, 0.85)';
            this.ctx.fillRect(0, 0, this.width, this.height);
            
            this.ctx.fillStyle = '#FF6B6B';
            this.ctx.font = 'bold 28px "Arial", "Courier New", monospace';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('GAME OVER', this.width/2, this.height/2 - 60);
            
            this.ctx.fillStyle = 'white';
            this.ctx.font = '22px "Arial", "Courier New", monospace';
            this.ctx.fillText(`Score: ${this.score}`, this.width/2, this.height/2 - 10);
            
            this.ctx.font = '16px "Arial", "Courier New", monospace';
            this.ctx.fillStyle = '#FFD700';
            this.ctx.fillText(`Level ${this.level} Reached`, this.width/2, this.height/2 + 30);
            
            this.ctx.fillStyle = '#88DED1';
            this.ctx.fillText(`Pipes: ${this.pipesPassed}`, this.width/2, this.height/2 + 60);
            
            this.ctx.fillStyle = 'white';
            this.ctx.font = '14px "Arial", "Courier New", monospace';
            this.ctx.fillText('Click or Press Space to Restart', this.width/2, this.height/2 + 110);
            
            this.ctx.textAlign = 'left';
        }
    }
    
    async updateScore() {
        await this.saveScore();
    }
    
    resetGame() {
        this.gameRunning = true;
        this.gameOver = false;
        this.score = 0;
        this.level = 1;
        this.pipesPassed = 0;
        this.currentPipeSpeed = this.basePipeSpeed;
        this.pipeGap = 180;
        this.bird.y = this.height / 2;
        this.bird.velocity = 0;
        this.bird.rotation = 0;
        this.pipes = [];
        this.gameplayData = [];
        this.startTime = Date.now();
        
        setTimeout(() => {
            if (this.gameRunning) {
                this.createPipe();
            }
        }, 500);
    }
    
    draw() {
        this.drawBackground();
        this.drawPipes();
        this.drawBird();
        this.drawScore();
        this.drawGameOver();
    }
    
    gameLoop() {
        this.update();
        this.draw();
        requestAnimationFrame(() => this.gameLoop());
    }
}

// Initialize game
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('gameCanvas')) {
        window.game = new FlappyBirdGame('gameCanvas');
    }
});
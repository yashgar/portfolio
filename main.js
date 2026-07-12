import * as THREE from 'three';

const themes = {
    dark: {
        backgroundColor: 0x000000,
        particleColor: 0x00aaff,
        lineColor: 0x00aaff
    },
    light: {
        backgroundColor: 0xf0f0f0,
        particleColor: 0x000000,
        lineColor: 0x000000
    }
};

let currentTheme = themes.dark;

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(
    75,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
);

camera.position.z = 25;

const renderer = new THREE.WebGLRenderer({
    canvas: document.getElementById('neural-network-canvas')
});

renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(currentTheme.backgroundColor, 1);

const brainGroup = new THREE.Group();

const particleCount = 1300;
const connectionDistance = 7;
const sphereRadius = 20;

const particlesGeometry = new THREE.BufferGeometry();
const particlePositions = [];

for (let i = 0; i < particleCount; i++) {
    const x = (Math.random() - 0.5) * sphereRadius * 2;
    const y = (Math.random() - 0.5) * sphereRadius * 2;
    const z = (Math.random() - 0.5) * sphereRadius * 2;

    const position = new THREE.Vector3(x, y, z);

    if (position.length() < sphereRadius) {
        particlePositions.push(x, y, z);
    }
}

particlesGeometry.setAttribute(
    'position',
    new THREE.Float32BufferAttribute(particlePositions, 3)
);

const particlesMaterial = new THREE.PointsMaterial({
    color: currentTheme.particleColor,
    size: 0.1,
    sizeAttenuation: true
});

const particles = new THREE.Points(
    particlesGeometry,
    particlesMaterial
);

brainGroup.add(particles);

const linesGeometry = new THREE.BufferGeometry();
const linePositions = [];

const positions = particles.geometry.attributes.position.array;
const actualParticleCount = positions.length / 3;

for (let i = 0; i < actualParticleCount; i++) {
    for (let j = i + 1; j < actualParticleCount; j++) {
        const dx = positions[i * 3] - positions[j * 3];
        const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
        const dz = positions[i * 3 + 2] - positions[j * 3 + 2];

        const distance = Math.sqrt(
            dx * dx +
            dy * dy +
            dz * dz
        );

        if (distance < connectionDistance) {
            linePositions.push(
                positions[i * 3],
                positions[i * 3 + 1],
                positions[i * 3 + 2]
            );

            linePositions.push(
                positions[j * 3],
                positions[j * 3 + 1],
                positions[j * 3 + 2]
            );
        }
    }
}

linesGeometry.setAttribute(
    'position',
    new THREE.Float32BufferAttribute(linePositions, 3)
);

const linesMaterial = new THREE.LineBasicMaterial({
    color: currentTheme.lineColor,
    transparent: true,
    opacity: 0.1
});

const lines = new THREE.LineSegments(
    linesGeometry,
    linesMaterial
);

brainGroup.add(lines);
scene.add(brainGroup);

function updateRotationOnScroll() {
    const scrollY = window.scrollY;

    brainGroup.rotation.y = scrollY * 0.001;
    brainGroup.rotation.x = scrollY * 0.0005;
}

window.addEventListener(
    'scroll',
    updateRotationOnScroll
);

function animate() {
    requestAnimationFrame(animate);

    brainGroup.rotation.y += 0.0002;
    brainGroup.rotation.x += 0.0001;

    renderer.render(scene, camera);
}

animate();

window.addEventListener('resize', () => {
    camera.aspect =
        window.innerWidth / window.innerHeight;

    camera.updateProjectionMatrix();

    renderer.setSize(
        window.innerWidth,
        window.innerHeight
    );

    renderer.setPixelRatio(
        Math.min(window.devicePixelRatio, 2)
    );
});

const themeToggleBtn =
    document.getElementById('theme-toggle-btn');

const sunIcon =
    document.getElementById('sun-icon');

const moonIcon =
    document.getElementById('moon-icon');

function setTheme(themeName) {
    const theme = themes[themeName];

    if (!theme) {
        return;
    }

    currentTheme = theme;

    renderer.setClearColor(
        theme.backgroundColor
    );

    particlesMaterial.color.setHex(
        theme.particleColor
    );

    linesMaterial.color.setHex(
        theme.lineColor
    );

    if (themeName === 'light') {
        document.body.classList.add('light-mode');

        sunIcon.style.display = 'none';
        moonIcon.style.display = 'block';
    } else {
        document.body.classList.remove('light-mode');

        sunIcon.style.display = 'block';
        moonIcon.style.display = 'none';
    }

    localStorage.setItem(
        'theme',
        themeName
    );
}

if (themeToggleBtn) {
    themeToggleBtn.addEventListener('click', () => {
        const current =
            localStorage.getItem('theme') || 'dark';

        const newTheme =
            current === 'dark'
                ? 'light'
                : 'dark';

        setTheme(newTheme);
    });
}

const savedTheme =
    localStorage.getItem('theme') || 'dark';

setTheme(savedTheme);

const fullscreenBtn =
    document.getElementById('fullscreen-btn');

const enterIcon =
    document.getElementById('fullscreen-enter-icon');

const exitIcon =
    document.getElementById('fullscreen-exit-icon');

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement
            .requestFullscreen()
            .catch(error => {
                alert(
                    `Error attempting to enable full-screen mode: ${error.message} (${error.name})`
                );
            });

        return;
    }

    if (document.exitFullscreen) {
        document.exitFullscreen();
    }
}

function updateFullscreenIcon() {
    if (document.fullscreenElement) {
        enterIcon.style.display = 'none';
        exitIcon.style.display = 'block';
    } else {
        enterIcon.style.display = 'block';
        exitIcon.style.display = 'none';
    }
}

if (fullscreenBtn) {
    fullscreenBtn.addEventListener(
        'click',
        toggleFullscreen
    );
}

document.addEventListener(
    'fullscreenchange',
    updateFullscreenIcon
);

const textElement =
    document.querySelector('.typing-text');

if (textElement) {
    const phrases = [
        'Computer Science Undergraduate.',
        'Machine Learning Enthusiast.',
        'Full Stack Developer.',
        'Problem Solver.'
    ];

    let phraseIndex = 0;
    let charIndex = 0;
    let isDeleting = false;

    function typeEffect() {
        const currentPhrase =
            phrases[phraseIndex];

        if (isDeleting) {
            textElement.textContent =
                currentPhrase.substring(
                    0,
                    charIndex--
                );
        } else {
            textElement.textContent =
                currentPhrase.substring(
                    0,
                    charIndex++
                );
        }

        let typeSpeed =
            isDeleting ? 50 : 100;

        if (
            !isDeleting &&
            charIndex === currentPhrase.length
        ) {
            typeSpeed = 2000;
            isDeleting = true;
        } else if (
            isDeleting &&
            charIndex === 0
        ) {
            isDeleting = false;

            phraseIndex =
                (phraseIndex + 1) %
                phrases.length;

            typeSpeed = 500;
        }

        setTimeout(
            typeEffect,
            typeSpeed
        );
    }

    typeEffect();
}

const observer = new IntersectionObserver(
    entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('show');
            }
        });
    }
);

const hiddenElements =
    document.querySelectorAll('.hidden');

hiddenElements.forEach(element => {
    observer.observe(element);
});

document.addEventListener(
    'DOMContentLoaded',
    () => {
        const container =
            document.querySelector(
                '.carousel-container'
            );

        const track =
            document.querySelector(
                '.carousel-track'
            );

        if (container && track) {
            const cards =
                Array.from(track.children);

            cards.forEach(card => {
                const clone =
                    card.cloneNode(true);

                track.appendChild(clone);
            });

            let isDown = false;
            let startX = 0;
            let scrollLeft = 0;
            let isDragging = false;

            const scrollSpeed = 0.5;

            let carouselAnimationId;

            const getResetPoint = () =>
                track.scrollWidth / 2;

            function autoScroll() {
                if (!isDown) {
                    container.scrollLeft +=
                        scrollSpeed;

                    if (
                        container.scrollLeft >=
                        getResetPoint()
                    ) {
                        container.scrollLeft = 0;
                    }
                }

                carouselAnimationId =
                    requestAnimationFrame(
                        autoScroll
                    );
            }

            carouselAnimationId =
                requestAnimationFrame(
                    autoScroll
                );

            container.addEventListener(
                'mousedown',
                event => {
                    isDown = true;
                    isDragging = false;

                    container.classList.add(
                        'active'
                    );

                    startX =
                        event.pageX -
                        container.offsetLeft;

                    scrollLeft =
                        container.scrollLeft;

                    cancelAnimationFrame(
                        carouselAnimationId
                    );
                }
            );

            container.addEventListener(
                'mouseleave',
                () => {
                    isDown = false;

                    container.classList.remove(
                        'active'
                    );

                    cancelAnimationFrame(
                        carouselAnimationId
                    );

                    carouselAnimationId =
                        requestAnimationFrame(
                            autoScroll
                        );
                }
            );

            container.addEventListener(
                'mouseup',
                () => {
                    isDown = false;

                    container.classList.remove(
                        'active'
                    );

                    setTimeout(() => {
                        if (!isDown) {
                            cancelAnimationFrame(
                                carouselAnimationId
                            );

                            carouselAnimationId =
                                requestAnimationFrame(
                                    autoScroll
                                );
                        }
                    }, 500);
                }
            );

            container.addEventListener(
                'mousemove',
                event => {
                    if (!isDown) {
                        return;
                    }

                    event.preventDefault();

                    isDragging = true;

                    const x =
                        event.pageX -
                        container.offsetLeft;

                    const walk =
                        (x - startX) * 2;

                    container.scrollLeft =
                        scrollLeft - walk;
                }
            );

            const links =
                container.querySelectorAll('a');

            links.forEach(link => {
                link.addEventListener(
                    'click',
                    event => {
                        if (isDragging) {
                            event.preventDefault();

                            isDragging = false;
                        }
                    }
                );
            });
        }

        const tiltCards =
            document.querySelectorAll(
                '.project-card, .certificate-card'
            );

        tiltCards.forEach(card => {
            card.addEventListener(
                'mousemove',
                event => {
                    const rect =
                        card.getBoundingClientRect();

                    const x =
                        event.clientX - rect.left;

                    const y =
                        event.clientY - rect.top;

                    const xRotation =
                        -(
                            (y - rect.height / 2) /
                            20
                        );

                    const yRotation =
                        (
                            (x - rect.width / 2) /
                            20
                        );

                    card.style.transform =
                        `perspective(1000px) rotateX(${xRotation}deg) rotateY(${yRotation}deg) scale(1.02)`;
                }
            );

            card.addEventListener(
                'mouseleave',
                () => {
                    card.style.transform =
                        'perspective(1000px) rotateX(0) rotateY(0) scale(1)';
                }
            );
        });
    }
);

const tetrisCanvas =
    document.getElementById('tetris-canvas');

const ctx =
    tetrisCanvas.getContext('2d');

const scoreElement =
    document.getElementById('tetris-score');

const startBtn =
    document.getElementById('start-tetris-btn');

const ROWS = 20;
const COLS = 12;
const BLOCK_SIZE = 20;

ctx.scale(
    BLOCK_SIZE,
    BLOCK_SIZE
);

const COLORS = [
    null,
    '#FF0D72',
    '#0DC2FF',
    '#0DFF72',
    '#F538FF',
    '#FF8E0D',
    '#FFE138',
    '#3877FF'
];

const PIECES = [
    [],
    [
        [0, 1, 0],
        [1, 1, 1],
        [0, 0, 0]
    ],
    [
        [0, 2, 0, 0],
        [0, 2, 0, 0],
        [0, 2, 0, 0],
        [0, 2, 0, 0]
    ],
    [
        [0, 3, 3],
        [3, 3, 0],
        [0, 0, 0]
    ],
    [
        [4, 4, 0],
        [0, 4, 4],
        [0, 0, 0]
    ],
    [
        [0, 5, 0],
        [0, 5, 0],
        [0, 5, 5]
    ],
    [
        [6, 6],
        [6, 6]
    ],
    [
        [0, 7, 0],
        [0, 7, 0],
        [7, 7, 0]
    ]
];

function createMatrix(width, height) {
    const matrix = [];

    while (height--) {
        matrix.push(
            new Array(width).fill(0)
        );
    }

    return matrix;
}

let arena =
    createMatrix(COLS, ROWS);

const player = {
    pos: {
        x: 0,
        y: 0
    },
    matrix: null,
    score: 0
};

let dropCounter = 0;
const dropInterval = 1000;
let lastTime = 0;
let gameActive = false;
let tetrisAnimationId = null;

function drawMatrix(matrix, offset) {
    matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value === 0) {
                return;
            }

            ctx.fillStyle =
                COLORS[value];

            ctx.fillRect(
                x + offset.x,
                y + offset.y,
                1,
                1
            );

            ctx.lineWidth = 0.05;
            ctx.strokeStyle = '#000';

            ctx.strokeRect(
                x + offset.x,
                y + offset.y,
                1,
                1
            );
        });
    });
}

function draw() {
    ctx.fillStyle = '#111';

    ctx.fillRect(
        0,
        0,
        tetrisCanvas.width / BLOCK_SIZE,
        tetrisCanvas.height / BLOCK_SIZE
    );

    drawMatrix(
        arena,
        {
            x: 0,
            y: 0
        }
    );

    if (player.matrix) {
        drawMatrix(
            player.matrix,
            player.pos
        );
    }
}

function merge(targetArena, currentPlayer) {
    currentPlayer.matrix.forEach(
        (row, y) => {
            row.forEach((value, x) => {
                if (value !== 0) {
                    targetArena[
                        y + currentPlayer.pos.y
                    ][
                        x + currentPlayer.pos.x
                    ] = value;
                }
            });
        }
    );
}

function collide(targetArena, currentPlayer) {
    const matrix =
        currentPlayer.matrix;

    const offset =
        currentPlayer.pos;

    for (
        let y = 0;
        y < matrix.length;
        y++
    ) {
        for (
            let x = 0;
            x < matrix[y].length;
            x++
        ) {
            if (
                matrix[y][x] !== 0 &&
                (
                    targetArena[y + offset.y] &&
                    targetArena[y + offset.y][x + offset.x]
                ) !== 0
            ) {
                return true;
            }
        }
    }

    return false;
}

function playerDrop() {
    player.pos.y++;

    if (collide(arena, player)) {
        player.pos.y--;

        merge(
            arena,
            player
        );

        playerReset();
        arenaSweep();
        updateScore();
    }

    dropCounter = 0;
}

function playerMove(offset) {
    player.pos.x += offset;

    if (collide(arena, player)) {
        player.pos.x -= offset;
    }
}

function playerReset() {
    const pieces = '1234567';

    const randomPiece =
        pieces[
            Math.floor(
                Math.random() *
                pieces.length
            )
        ];

    player.matrix =
        PIECES[randomPiece];

    player.pos.y = 0;

    player.pos.x =
        Math.floor(
            arena[0].length / 2
        ) -
        Math.floor(
            player.matrix[0].length / 2
        );

    if (collide(arena, player)) {
        arena.forEach(row => {
            row.fill(0);
        });

        gameActive = false;

        startBtn.innerText =
            'Game Over! Play Again';
    }
}

function playerRotate(direction) {
    const originalPosition =
        player.pos.x;

    let offset = 1;

    rotate(
        player.matrix,
        direction
    );

    while (collide(arena, player)) {
        player.pos.x += offset;

        offset =
            -(
                offset +
                (
                    offset > 0
                        ? 1
                        : -1
                )
            );

        if (
            offset >
            player.matrix[0].length
        ) {
            rotate(
                player.matrix,
                -direction
            );

            player.pos.x =
                originalPosition;

            return;
        }
    }
}

function rotate(matrix, direction) {
    for (
        let y = 0;
        y < matrix.length;
        y++
    ) {
        for (
            let x = 0;
            x < y;
            x++
        ) {
            [
                matrix[x][y],
                matrix[y][x]
            ] = [
                matrix[y][x],
                matrix[x][y]
            ];
        }
    }

    if (direction > 0) {
        matrix.forEach(row => {
            row.reverse();
        });
    } else {
        matrix.reverse();
    }
}

function arenaSweep() {
    let rowCount = 1;

    outer:
    for (
        let y = arena.length - 1;
        y >= 0;
        y--
    ) {
        for (
            let x = 0;
            x < arena[y].length;
            x++
        ) {
            if (arena[y][x] === 0) {
                continue outer;
            }
        }

        const row =
            arena
                .splice(y, 1)[0]
                .fill(0);

        arena.unshift(row);

        y++;

        player.score +=
            rowCount * 10;

        rowCount *= 2;
    }
}

function updateScore() {
    scoreElement.innerText =
        player.score;
}

function update(time = 0) {
    if (!gameActive) {
        return;
    }

    const deltaTime =
        time - lastTime;

    lastTime = time;

    dropCounter += deltaTime;

    let currentDropInterval =
        dropInterval -
        (
            Math.floor(
                player.score / 50
            ) * 100
        );

    if (currentDropInterval < 150) {
        currentDropInterval = 150;
    }

    if (
        dropCounter >
        currentDropInterval
    ) {
        playerDrop();
    }

    draw();

    tetrisAnimationId =
        requestAnimationFrame(update);
}

document.addEventListener(
    'keydown',
    event => {
        if (!gameActive) {
            return;
        }

        const arrowKeys = [
            'ArrowUp',
            'ArrowDown',
            'ArrowLeft',
            'ArrowRight'
        ];

        if (
            arrowKeys.includes(event.code)
        ) {
            event.preventDefault();
        }

        switch (event.key) {
            case 'ArrowLeft':
                playerMove(-1);
                break;

            case 'ArrowRight':
                playerMove(1);
                break;

            case 'ArrowDown':
                playerDrop();
                break;

            case 'ArrowUp':
                playerRotate(1);
                break;
        }
    }
);

startBtn.addEventListener(
    'click',
    () => {
        if (gameActive) {
            gameActive = false;

            startBtn.innerText =
                'Resume Game';

            cancelAnimationFrame(
                tetrisAnimationId
            );

            return;
        }

        if (
            startBtn.innerText.includes(
                'Game Over'
            )
        ) {
            player.score = 0;

            updateScore();
        }

        if (!player.matrix) {
            playerReset();
        }

        gameActive = true;

        startBtn.innerText =
            'Pause Game';

        lastTime = performance.now();

        update(lastTime);
    }
);

draw();

const cursor =
    document.querySelector(
        '.custom-cursor'
    );

if (cursor) {
    document.addEventListener(
        'mousemove',
        event => {
            cursor.style.transform =
                `translate3d(calc(${event.clientX}px - 50%), calc(${event.clientY}px - 50%), 0)`;
        }
    );

    const interactiveElements =
        document.querySelectorAll(
            'a, button, input, textarea, .project-card, .certificate-card'
        );

    interactiveElements.forEach(element => {
        element.addEventListener(
            'mouseenter',
            () => {
                cursor.classList.add(
                    'hovering'
                );
            }
        );

        element.addEventListener(
            'mouseleave',
            () => {
                cursor.classList.remove(
                    'hovering'
                );
            }
        );
    });
}

const badgeCards =
    document.querySelectorAll(
        '.badge-card'
    );

badgeCards.forEach(card => {
    card.addEventListener(
        'click',
        () => {
            card.classList.toggle(
                'active'
            );
        }
    );

    card.addEventListener(
        'mouseenter',
        () => {
            if (cursor) {
                cursor.classList.add(
                    'hovering'
                );
            }
        }
    );

    card.addEventListener(
        'mouseleave',
        () => {
            if (cursor) {
                cursor.classList.remove(
                    'hovering'
                );
            }
        }
    );
});
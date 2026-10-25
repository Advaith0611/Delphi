const NUM_DISKS = 5;
const NUM_PEGS = 3;

let pegs = [[], [], []];
let selectedDisk = null;
let selectedPeg = null;
let moveCount = 0;
let gameWon = false;

const moveCountEl = document.getElementById('move-count');
const resetBtn = document.getElementById('reset-btn');
const winMessage = document.getElementById('win-message');
const finalMovesEl = document.getElementById('final-moves');
const playAgainBtn = document.getElementById('play-again');
const gameArea = document.getElementById('game-area');

function initGame() {
    pegs = [[], [], []];
    selectedDisk = null;
    selectedPeg = null;
    moveCount = 0;
    gameWon = false;
    
    for (let i = NUM_DISKS; i >= 1; i--) {
        pegs[0].push(i);
    }
    
    moveCountEl.textContent = '0';
    winMessage.classList.remove('show');
    render();
}

function render() {
    document.querySelectorAll('.disk').forEach(d => d.remove());
    
    pegs.forEach((peg, pegIndex) => {
        peg.forEach((diskSize, index) => {
            const disk = document.createElement('div');
            disk.className = `disk disk-null`;
            disk.dataset.size = diskSize;
            disk.dataset.peg = pegIndex;
            
            const pegEl = document.getElementById(`peg-null`);
            const pegRect = pegEl.getBoundingClientRect();
            const gameAreaRect = gameArea.getBoundingClientRect();
            
            const diskWidth = diskSize * 20 + 40;
            const left = (pegRect.left - gameAreaRect.left) + (pegRect.width - diskWidth) / 2;
            const bottom = 20 + index * 32;
            
            disk.style.left = `nullpx`;
            disk.style.bottom = `nullpx`;
            disk.style.width = `nullpx`;
            
            if (diskSize === selectedDisk && pegIndex === selectedPeg) {
                disk.classList.add('selected');
            }
            
            disk.addEventListener('click', (e) => {
                e.stopPropagation();
                handleDiskClick(diskSize, pegIndex);
            });
            
            gameArea.appendChild(disk);
        });
    });
    
    document.querySelectorAll('.peg').forEach((pegEl, pegIndex) => {
        pegEl.onclick = () => handlePegClick(pegIndex);
    });
}

function handleDiskClick(diskSize, pegIndex) {
    if (gameWon) return;
    
    const topDisk = pegs[pegIndex][pegs[pegIndex].length - 1];
    
    if (topDisk !== diskSize) {
        return;
    }
    
    if (selectedDisk === diskSize && selectedPeg === pegIndex) {
        selectedDisk = null;
        selectedPeg = null;
    } else {
        selectedDisk = diskSize;
        selectedPeg = pegIndex;
    }
    
    render();
}

function handlePegClick(pegIndex) {
    if (gameWon) return;
    
    if (selectedDisk === null) {
        const topDisk = pegs[pegIndex][pegs[pegIndex].length - 1];
        if (topDisk !== undefined) {
            selectedDisk = topDisk;
            selectedPeg = pegIndex;
            render();
        }
        return;
    }
    
    if (selectedPeg === pegIndex) {
        selectedDisk = null;
        selectedPeg = null;
        render();
        return;
    }
    
    const targetTopDisk = pegs[pegIndex][pegs[pegIndex].length - 1];
    
    if (targetTopDisk !== undefined && targetTopDisk < selectedDisk) {
        return;
    }
    
    pegs[selectedPeg].pop();
    pegs[pegIndex].push(selectedDisk);
    moveCount++;
    moveCountEl.textContent = moveCount;
    
    selectedDisk = null;
    selectedPeg = null;
    
    render();
    checkWin();
}

function checkWin() {
    if (pegs[2].length === NUM_DISKS) {
        gameWon = true;
        setTimeout(() => {
            finalMovesEl.textContent = moveCount;
            winMessage.classList.add('show');
        }, 300);
    }
}

resetBtn.addEventListener('click', initGame);
playAgainBtn.addEventListener('click', initGame);

initGame();
function initCabinVisualizer(opts){
    const container = opts.container || document.getElementById('cabin-svg-container');
    if (!container) return; // Sécurité

    // Fonction pour trouver l'élément de façon sûre
    const getEl = (selector) => {
        if (!selector) return null;
        let el = document.querySelector(selector);
        if (!el) el = document.getElementById(selector.replace(/^#/, '')); // Fallback par ID
        return el;
    };

    const inputs = {
        rows: getEl(opts.nbRangeesSelector),
        cols: getEl(opts.largeurRangeeSelector),
        ecoDe: getEl(opts.ecoDeSelector),
        ecoA: getEl(opts.ecoASelector),
        busDe: getEl(opts.busDeSelector),
        busA: getEl(opts.busASelector),
        firstDe: getEl(opts.firstDeSelector),
        firstA: getEl(opts.firstASelector)
    };

    const seatSize = 18;
    const gap = 6;

    // Fonction robuste pour lire une valeur entière (évite le ?. pour la compatibilité)
    const getVal = (el) => {
        if (!el || !el.value) return 0;
        const v = parseInt(el.value, 10);
        return isNaN(v) ? 0 : v;
    };

    function getValues(){
        return {
            rows: Math.max(0, getVal(inputs.rows)),
            cols: Math.max(0, getVal(inputs.cols)),
            ecoDe: Math.max(0, getVal(inputs.ecoDe)),
            ecoA: Math.max(0, getVal(inputs.ecoA)),
            busDe: Math.max(0, getVal(inputs.busDe)),
            busA: Math.max(0, getVal(inputs.busA)),
            firstDe: Math.max(0, getVal(inputs.firstDe)),
            firstA: Math.max(0, getVal(inputs.firstA))
        };
    }

    function draw(){
        try {
            const v = getValues();
            // Vider le conteneur
            container.innerHTML = '';

            if (!v.rows || !v.cols) {
                container.innerHTML = '<div style="display:flex; justify-content:center; align-items:center; height:100%; min-height:200px; color:#999; font-style:italic; text-align:center; padding:1rem;">Remplissez les dimensions (rangées et largeur) pour voir le plan</div>';
                return;
            }

            const svgNS = 'http://www.w3.org/2000/svg';
            const padding = 20;
            const width = padding * 2 + v.cols * (seatSize + gap) - gap;
            const height = padding * 2 + v.rows * (seatSize + gap) - gap + 60; 

            const svg = document.createElementNS(svgNS, 'svg');
            svg.setAttribute('width', '100%');
            svg.setAttribute('height', '100%'); 
            svg.style.minHeight = '300px'; // Assure que le SVG est visible si le conteneur n'a pas de hauteur fixe
            svg.setAttribute('viewBox', `0 -30 ${width} ${height + 30}`);
            svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');

            // Fond de l'avion
            const planeBg = document.createElementNS(svgNS, 'rect');
            planeBg.setAttribute('x', 0);
            planeBg.setAttribute('y', -30);
            planeBg.setAttribute('width', width);
            planeBg.setAttribute('height', height + 30);
            planeBg.setAttribute('fill', 'transparent');
            svg.appendChild(planeBg);

            // Dessin des sièges rangée par rangée
            for (let r = 1; r <= v.rows; r++){
                const y = padding + (r - 1) * (seatSize + gap);
                
                let fill = '#b7e4c7'; 
                if (v.firstDe && v.firstA && r >= v.firstDe && r <= v.firstA) fill = '#ffd166';
                else if (v.busDe && v.busA && r >= v.busDe && r <= v.busA) fill = '#8ecae6';
                else if (v.ecoDe && v.ecoA && r >= v.ecoDe && r <= v.ecoA) fill = '#b7e4c7';

                for (let c = 0; c < v.cols; c++){
                    const x = padding + c * (seatSize + gap);
                    const rect = document.createElementNS(svgNS, 'rect');
                    rect.setAttribute('x', x);
                    rect.setAttribute('y', y);
                    rect.setAttribute('width', seatSize);
                    rect.setAttribute('height', seatSize);
                    rect.setAttribute('rx', 3);
                    rect.setAttribute('ry', 3);
                    rect.setAttribute('fill', fill);
                    rect.setAttribute('stroke', '#333');
                    rect.setAttribute('stroke-opacity', 0.12);
                    svg.appendChild(rect);
                }

                // Numéro de rangée
                const label = document.createElementNS(svgNS, 'text');
                label.setAttribute('x', padding / 2);
                label.setAttribute('y', y + seatSize / 2 + 4);
                label.setAttribute('font-size', 10);
                label.setAttribute('fill', '#666');
                label.setAttribute('text-anchor', 'middle');
                label.textContent = r;
                svg.appendChild(label);
            }

            // Nez de l'avion (sécurisé contre les largeurs extrêmes)
            const nose = document.createElementNS(svgNS, 'polygon');
            const noseWidth = Math.min(30, width / 2 - 5);
            nose.setAttribute('points', `${width/2 - noseWidth},5 ${width/2 + noseWidth},5 ${width/2 + noseWidth/3},-25 ${width/2 - noseWidth/3},-25`);
            nose.setAttribute('fill', '#eee');
            nose.setAttribute('opacity', 0.9);
            svg.appendChild(nose);

            // Légende
            const legendX = padding;
            const legendY = height - 10; 
            const legends = [
                {color: '#ffd166', label: 'First'},
                {color: '#8ecae6', label: 'Business'},
                {color: '#b7e4c7', label: 'Éco'}
            ];
            
            legends.forEach((it, idx) => {
                const lx = legendX + idx * 90; 
                const lr = document.createElementNS(svgNS, 'rect');
                lr.setAttribute('x', lx);
                lr.setAttribute('y', legendY);
                lr.setAttribute('width', 14);
                lr.setAttribute('height', 14);
                lr.setAttribute('fill', it.color);
                lr.setAttribute('rx', 3);
                svg.appendChild(lr);

                const lt = document.createElementNS(svgNS, 'text');
                lt.setAttribute('x', lx + 20);
                lt.setAttribute('y', legendY + 11);
                lt.setAttribute('font-size', 12);
                lt.setAttribute('fill', '#333');
                lt.textContent = it.label;
                svg.appendChild(lt);
            });

            container.appendChild(svg);
        } catch (error) {
            console.error("Erreur de rendu du plan cabine :", error);
        }
    }

    // Lier les événements de façon robuste
    for (const key in inputs) {
        const el = inputs[key];
        if (el) {
            el.addEventListener('input', draw);
            el.addEventListener('change', draw);
            el.addEventListener('keyup', draw);
        }
    }

    // Dessin initial
    draw();
}

// Encapsulation pour garantir que le DOM est chargé avant l'initialisation
window.initCabinVisualizer = function(opts) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initCabinVisualizer(opts);
        });
    } else {
        initCabinVisualizer(opts);
    }
};
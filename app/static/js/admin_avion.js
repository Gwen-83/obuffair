/**
 * Visualiseur de cabine d'avion - Rendu SVG interactif
 * Affiche un plan cabine vide au chargement, puis se met à jour en temps réel
 */
window.CabinVisualizer = class {
    constructor(opts) {
        this.container = opts.container;
        if (!this.container) {
            console.error('❌ CabinVisualizer: Container introuvable');
            return;
        }

        // Récupérer les inputs pour la configuration
        this.inputs = {
            rows: document.querySelector(opts.nbRangeesSelector),
            cols: document.querySelector(opts.largeurRangeeSelector),
            ecoDe: document.querySelector(opts.ecoDeSelector),
            ecoA: document.querySelector(opts.ecoASelector),
            busDe: document.querySelector(opts.busDeSelector),
            busA: document.querySelector(opts.busASelector),
            firstDe: document.querySelector(opts.firstDeSelector),
            firstA: document.querySelector(opts.firstASelector)
        };

        // Vérifier que tous les inputs sont trouvés
        const missing = [];
        for (const [key, el] of Object.entries(this.inputs)) {
            if (!el) {
                missing.push(`${key} (${Object.values(opts).find(v => typeof v === 'string' && v.includes(key))})`);
            }
        }
        
        if (missing.length > 0) {
            console.warn('⚠️ CabinVisualizer: Inputs manquants:', missing);
        }

        this.seatSize = 18;
        this.gap = 6;

        // Attacher les listeners d'events
        this.attachListeners();

        // Dessin initial
        this.draw();

        console.log('✅ CabinVisualizer initialisé');
    }

    getVal(el) {
        if (!el || !el.value) return 0;
        const v = parseInt(el.value, 10);
        return isNaN(v) ? 0 : v;
    }

    getValues() {
        return {
            rows: Math.max(0, this.getVal(this.inputs.rows)),
            cols: Math.max(0, this.getVal(this.inputs.cols)),
            ecoDe: Math.max(0, this.getVal(this.inputs.ecoDe)),
            ecoA: Math.max(0, this.getVal(this.inputs.ecoA)),
            busDe: Math.max(0, this.getVal(this.inputs.busDe)),
            busA: Math.max(0, this.getVal(this.inputs.busA)),
            firstDe: Math.max(0, this.getVal(this.inputs.firstDe)),
            firstA: Math.max(0, this.getVal(this.inputs.firstA))
        };
    }

    attachListeners() {
        const onUpdate = () => this.draw();
        
        for (const el of Object.values(this.inputs)) {
            if (el) {
                el.addEventListener('input', onUpdate);
                el.addEventListener('change', onUpdate);
                el.addEventListener('keyup', onUpdate);
            }
        }
    }

    draw() {
        try {
            const v = this.getValues();
            this.container.innerHTML = '';

            // Afficher vide au chargement (avant que l'utilisateur rentre des données)
            if (!v.rows || !v.cols) {
                this.container.innerHTML = `
                    <div style="display:flex; justify-content:center; align-items:center; height:100%; min-height:200px; color:#aaa; font-style:italic; text-align:center; padding:1rem; background-color: var(--light); border-radius: 4px;">
                        <span>Plan cabine vide - Remplissez les dimensions pour commencer</span>
                    </div>
                `;
                return;
            }

            const svgNS = 'http://www.w3.org/2000/svg';
            const padding = 20;

            // Déterminer positions des allées selon le nombre de colonnes
            const computeAisles = (cols) => {
                const aisles = [];
                if (cols >= 2 && cols <= 6) {
                    aisles.push(Math.floor(cols / 2));
                } else if (cols > 6) {
                    aisles.push(Math.floor(cols / 3));
                    aisles.push(Math.floor((2 * cols) / 3));
                }
                return [...new Set(aisles.filter(i => i > 0 && i < cols))];
            };

            const aisleIndices = computeAisles(v.cols);
            const extraGap = this.gap * 4; // espace supplémentaire pour une allée
            const totalExtra = aisleIndices.length * extraGap;

            const width = padding * 2 + v.cols * (this.seatSize + this.gap) - this.gap + totalExtra;
            const height = padding * 2 + v.rows * (this.seatSize + this.gap) - this.gap + 80;

            // Calculer largeur de viewport pour centrer correctement les sièges
            const seatsTotalWidth = v.cols * (this.seatSize + this.gap) - this.gap + totalExtra;
            const viewportWidth = Math.max(width, seatsTotalWidth + padding * 2, 600);
            const seatsStartX = Math.max(padding, Math.floor((viewportWidth - seatsTotalWidth) / 2));

            const svg = document.createElementNS(svgNS, 'svg');
            // Si très grand (beaucoup de rangées), garder la taille réelle et activer le scroll
            const maxHeightVisible = 700;
            if (height > maxHeightVisible) {
                svg.setAttribute('width', `${viewportWidth}`);
                svg.setAttribute('height', `${height + 10}`);
                svg.setAttribute('viewBox', `0 -30 ${viewportWidth} ${height + 30}`);
                svg.style.display = 'block';
                this.container.style.overflow = 'auto';
                this.container.style.maxHeight = `${maxHeightVisible}px`;
            } else {
                svg.setAttribute('width', '100%');
                svg.setAttribute('height', '100%');
                svg.setAttribute('viewBox', `0 -30 ${viewportWidth} ${height + 30}`);
                svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
                svg.style.minHeight = '400px';
                this.container.style.overflow = 'visible';
                this.container.style.maxHeight = '';
            }
            // Pas de carlingue détaillée : on affiche seulement les sièges centrés.

            // Normaliser et clamp des plages de classes (1-based rows)
            const classNames = { eco: 'Éco', business: 'Business', first: 'First' };
            const classInputs = [v.ecoDe, v.ecoA, v.busDe, v.busA, v.firstDe, v.firstA];
            const hasAnyClassValue = classInputs.some(value => value > 0);
            const warnings = [];

            const normalizeRange = (name, start, end) => {
                const label = classNames[name];
                const hasStart = Number.isFinite(start);
                const hasEnd = Number.isFinite(end);
                const rawStart = hasStart ? Math.floor(start) : null;
                const rawEnd = hasEnd ? Math.floor(end) : null;
                const range = {
                    rawStart,
                    rawEnd,
                    start: rawStart ?? 0,
                    end: rawEnd ?? 0,
                    valid: true,
                    absent: false,
                    label
                };

                if (rawStart === 0 && rawEnd === 0) {
                    range.valid = false;
                    range.absent = true;
                    return range;
                }

                if (!hasStart || !hasEnd) {
                    range.valid = false;
                    if (hasAnyClassValue) {
                        warnings.push(`Remplissez les deux bornes de la classe ${label}.`);
                    }
                    return range;
                }

                if (rawStart === 0 || rawEnd === 0) {
                    range.valid = false;
                    warnings.push(`La classe ${label} doit être définie soit entièrement, soit en 0-0.`);
                    return range;
                }

                if (range.start < 1 || range.end < 1) {
                    range.valid = false;
                    warnings.push(`Les rangées de ${label} doivent être supérieures ou égales à 1.`);
                }

                if (range.end < range.start) {
                    range.valid = false;
                    warnings.push(`La rangée de fin de ${label} doit être supérieure ou égale à la rangée de début.`);
                }

                if (range.start > v.rows || range.end > v.rows) {
                    range.valid = false;
                    warnings.push(`La plage ${label} dépasse le nombre total de rangées (${v.rows}).`);
                }

                range.start = Math.max(1, Math.min(range.start, v.rows));
                range.end = Math.max(0, Math.min(range.end, v.rows));
                return range;
            };

            const firstRange = normalizeRange('first', v.firstDe, v.firstA);
            const busRange = normalizeRange('business', v.busDe, v.busA);
            const ecoRange = normalizeRange('eco', v.ecoDe, v.ecoA);

            if (firstRange.valid && busRange.valid && firstRange.end >= busRange.start) {
                warnings.push('La classe Business doit commencer après le First.');
            }
            if (busRange.valid && ecoRange.valid && busRange.end >= ecoRange.start) {
                warnings.push('La classe Éco doit commencer après le Business.');
            }

            const assignedRows = new Set();
            const assignRange = (range) => {
                if (!range.valid) return;
                for (let row = range.start; row <= range.end; row += 1) {
                    assignedRows.add(row);
                }
            };
            assignRange(ecoRange);
            assignRange(busRange);
            assignRange(firstRange);

            if (hasAnyClassValue && assignedRows.size < v.rows) {
                warnings.push(`Il reste ${v.rows - assignedRows.size} rangée(s) sans classe définie.`);
            }

            const renderWarnings = () => {
                if (!warnings.length) return;
                const notice = document.createElement('div');
                notice.setAttribute('style', 'margin-bottom:14px;padding:12px 14px;border-left:3px solid #f1c40f;background:#fff7e0;color:#5f4b1f;border-radius:8px;font-size:13px;line-height:1.5;');
                notice.innerHTML = `<strong>Avertissements :</strong><br>${warnings.map(msg => `<div>${msg}</div>`).join('')}`;
                this.container.appendChild(notice);
            };

            renderWarnings();

            // Dessin des sièges rangée par rangée
            for (let r = 1; r <= v.rows; r++) {
                const y = padding + (r - 1) * (this.seatSize + this.gap);

                // Déterminer la couleur selon la classe (priorité First > Bus > Éco)
                let fill = '#f3f4f6';
                if (firstRange.valid && r >= firstRange.start && r <= firstRange.end) {
                    fill = '#ffd166';
                } else if (busRange.valid && r >= busRange.start && r <= busRange.end) {
                    fill = '#8ecae6';
                } else if (ecoRange.valid && r >= ecoRange.start && r <= ecoRange.end) {
                    fill = '#b7e4c7';
                }

                // Créer les sièges en tenant compte des allées (positions centrées)
                for (let c = 0; c < v.cols; c++) {
                    const aislesBefore = aisleIndices.filter(idx => c >= idx).length;
                    const x = seatsStartX + c * (this.seatSize + this.gap) + aislesBefore * extraGap;
                    const rect = document.createElementNS(svgNS, 'rect');
                    rect.setAttribute('x', x);
                    rect.setAttribute('y', y);
                    rect.setAttribute('width', this.seatSize);
                    rect.setAttribute('height', this.seatSize);
                    rect.setAttribute('rx', 3);
                    rect.setAttribute('ry', 3);
                    rect.setAttribute('fill', fill);
                    rect.setAttribute('stroke', '#bfc8cf');
                    rect.setAttribute('stroke-width', 1);
                    svg.appendChild(rect);
                }

                // Numéro de rangée
                const label = document.createElementNS(svgNS, 'text');
                label.setAttribute('x', Math.max(12, padding / 2 - 5));
                label.setAttribute('y', y + this.seatSize / 2 + 4);
                label.setAttribute('font-size', '11');
                label.setAttribute('font-weight', '600');
                label.setAttribute('fill', '#666');
                label.setAttribute('text-anchor', 'middle');
                label.textContent = r;
                svg.appendChild(label);
            }

            // Labels avant/arrière
            const labelFront = document.createElementNS(svgNS, 'text');
            labelFront.setAttribute('x', viewportWidth / 2);
            labelFront.setAttribute('y', -10);
            labelFront.setAttribute('font-size', '13');
            labelFront.setAttribute('font-weight', '700');
            labelFront.setAttribute('fill', '#333');
            labelFront.setAttribute('text-anchor', 'middle');
            labelFront.textContent = 'Avant';
            svg.appendChild(labelFront);

            const labelRear = document.createElementNS(svgNS, 'text');
            labelRear.setAttribute('x', viewportWidth / 2);
            labelRear.setAttribute('y', height - 5);
            labelRear.setAttribute('font-size', '13');
            labelRear.setAttribute('font-weight', '700');
            labelRear.setAttribute('fill', '#333');
            labelRear.setAttribute('text-anchor', 'middle');
            labelRear.textContent = 'Arrière';
            svg.appendChild(labelRear);

            // Légende
            const legendY = height - 15;
            const legends = [
                { color: '#ffd166', label: 'First' },
                { color: '#8ecae6', label: 'Business' },
                { color: '#b7e4c7', label: 'Éco' }
            ];

            legends.forEach((item, idx) => {
                const lx = padding + idx * 110;

                const rect = document.createElementNS(svgNS, 'rect');
                rect.setAttribute('x', lx);
                rect.setAttribute('y', legendY);
                rect.setAttribute('width', 12);
                rect.setAttribute('height', 12);
                rect.setAttribute('fill', item.color);
                rect.setAttribute('rx', 2);
                svg.appendChild(rect);

                const text = document.createElementNS(svgNS, 'text');
                text.setAttribute('x', lx + 18);
                text.setAttribute('y', legendY + 10);
                text.setAttribute('font-size', '11');
                text.setAttribute('fill', '#555');
                text.textContent = item.label;
                svg.appendChild(text);
            });

            this.container.appendChild(svg);
        } catch (error) {
            console.error('❌ Erreur de rendu du plan cabine:', error);
            this.container.innerHTML = '<div style="color: red; padding: 1rem;">Erreur lors du rendu du plan cabine</div>';
        }
    }
};

/**
 * Initialisation compatible - supporte les deux approches
 */
window.initCabinVisualizer = function(opts) {
    // S'assurer que le DOM est complètement prêt
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            new window.CabinVisualizer(opts);
        });
    } else {
        new window.CabinVisualizer(opts);
    }
};
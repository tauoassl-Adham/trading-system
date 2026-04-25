// Trading Intelligence System Dashboard
class Dashboard {
    constructor() {
        this.apiBase = 'http://127.0.0.1:8000';
        this.updateInterval = 5000; // تحديث كل 5 ثواني
        this.init();
    }

    async init() {
        await this.checkStatus();
        this.startUpdates();
    }

    async checkStatus() {
        try {
            const response = await fetch(`${this.apiBase}/`);
            if (response.ok) {
                document.getElementById('status-dot').classList.add('online');
                document.getElementById('status-text').textContent = 'متصل ✅';
            } else {
                throw new Error('Server not responding');
            }
        } catch (error) {
            document.getElementById('status-text').textContent = 'غير متصل ❌';
            console.error('Status check failed:', error);
        }
    }

    startUpdates() {
        this.updateAll();
        setInterval(() => this.updateAll(), this.updateInterval);
    }

    async updateAll() {
        await Promise.all([
            this.updateSnapshot(),
            this.updatePortfolio(),
            this.updateRisk(),
            this.updateSignals(),
            this.updateAnalytics(),
            this.updatePositions(),
            this.updateTrades(),
            this.updateSuggestions()
        ]);
    }

    async updateSnapshot() {
        try {
            const response = await fetch(`${this.apiBase}/snapshot`);
            const data = await response.json();

            document.getElementById('current-price').textContent =
                data.price ? `$${data.price.toLocaleString()}` : '--';

            this.updateTrend('trend-15m', data.trend_15m);
            this.updateTrend('trend-1h', data.trend_1h);
            this.updateTrend('trend-1d', data.trend_1d);

        } catch (error) {
            console.error('Snapshot update failed:', error);
        }
    }

    updateTrend(elementId, trend) {
        const element = document.getElementById(elementId);
        if (!element) return;

        element.textContent = this.translateTrend(trend);
        element.className = `value ${trend}`;
    }

    translateTrend(trend) {
        const translations = {
            'bullish': 'صاعد 📈',
            'bearish': 'هابط 📉',
            'neutral': 'محايد ➡️'
        };
        return translations[trend] || trend || '--';
    }

    async updatePortfolio() {
        try {
            const response = await fetch(`${this.apiBase}/portfolio`);
            const data = await response.json();

            const metrics = data.metrics;
            document.getElementById('total-value').textContent =
                `$${metrics.total_value.toLocaleString()}`;
            document.getElementById('available-balance').textContent =
                `$${metrics.available_balance.toLocaleString()}`;
            document.getElementById('total-pnl').textContent =
                `$${metrics.total_pnl.toFixed(2)}`;
            document.getElementById('total-pnl').className =
                `value ${metrics.total_pnl >= 0 ? 'positive' : 'negative'}`;
            document.getElementById('total-trades').textContent = metrics.total_trades;

            this.updatePositionsList(data.positions);

        } catch (error) {
            console.error('Portfolio update failed:', error);
        }
    }

    async updateRisk() {
        try {
            const response = await fetch(`${this.apiBase}/risk`);
            const data = await response.json();

            document.getElementById('daily-loss').textContent =
                `$${data.daily_loss.toFixed(2)}`;
            document.getElementById('daily-limit').textContent =
                `$${data.daily_loss_limit.toFixed(2)}`;
            document.getElementById('active-positions').textContent = data.active_positions;
            document.getElementById('total-exposure').textContent =
                `$${data.total_exposure.toFixed(2)}`;

        } catch (error) {
            console.error('Risk update failed:', error);
        }
    }

    async updateSignals() {
        try {
            const response = await fetch(`${this.apiBase}/signals`);
            const data = await response.json();

            const signalElement = document.getElementById('trend-signal');
            const signal = data.trend_following;

            if (signal) {
                const direction = signal.direction === 'BUY' ? 'شراء 🟢' : 'بيع 🔴';
                signalElement.textContent = `${direction} @ $${signal.entry_price.toFixed(2)}`;
                signalElement.className = `signal-status ${signal.direction.toLowerCase()}`;
            } else {
                signalElement.textContent = 'لا توجد إشارة';
                signalElement.className = 'signal-status none';
            }

        } catch (error) {
            console.error('Signals update failed:', error);
        }
    }

    async updateAnalytics() {
        try {
            const response = await fetch(`${this.apiBase}/analytics`);
            const data = await response.json();

            const performance = data.performance;
            document.getElementById('win-rate').textContent =
                `${(performance.win_rate * 100).toFixed(1)}%`;
            document.getElementById('profit-factor').textContent =
                performance.profit_factor.toFixed(2);
            document.getElementById('sharpe-ratio').textContent =
                performance.sharpe_ratio.toFixed(2);
            document.getElementById('max-drawdown').textContent =
                `$${performance.max_drawdown.toFixed(2)}`;

        } catch (error) {
            console.error('Analytics update failed:', error);
        }
    }

    updatePositionsList(positions) {
        const container = document.getElementById('positions-container');

        if (!positions || positions.length === 0) {
            container.innerHTML = '<p class="no-data">لا توجد مراكز نشطة</p>';
            return;
        }

        container.innerHTML = positions.map(position => `
            <div class="position-item">
                <div><strong>${position.symbol}</strong></div>
                <div>${position.side === 'long' ? 'شراء' : 'بيع'}</div>
                <div>${position.quantity}</div>
                <div class="${position.unrealized_pnl >= 0 ? 'positive' : 'negative'}">
                    $${position.unrealized_pnl.toFixed(2)}
                </div>
            </div>
        `).join('');
    }

    async updateTrades() {
        try {
            const response = await fetch(`${this.apiBase}/trades`);
            const trades = await response.json();

            const container = document.getElementById('trades-container');

            if (!trades || trades.length === 0) {
                container.innerHTML = '<p class="no-data">لا توجد تداولات حديثة</p>';
                return;
            }

            container.innerHTML = trades.slice(0, 5).map(trade => `
                <div class="trade-item ${trade.pnl >= 0 ? 'profit' : 'loss'}">
                    <div><strong>${trade.symbol}</strong></div>
                    <div>${trade.direction}</div>
                    <div>$${trade.entry_price.toFixed(2)}</div>
                    <div class="${trade.pnl >= 0 ? 'positive' : 'negative'}">
                        $${trade.pnl.toFixed(2)}
                    </div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Trades update failed:', error);
        }
    }

    async updateSuggestions() {
        try {
            const response = await fetch(`${this.apiBase}/analytics/suggestions`);
            const data = await response.json();

            const container = document.getElementById('suggestions-container');

            if (!data.suggestions || data.suggestions.length === 0) {
                container.innerHTML = '<div class="suggestion-item"><span class="suggestion-text">الأداء جيد - استمر في نفس الاستراتيجية</span></div>';
                return;
            }

            container.innerHTML = data.suggestions.map(suggestion => `
                <div class="suggestion-item">
                    <span class="suggestion-text">${suggestion}</span>
                </div>
            `).join('');

        } catch (error) {
            console.error('Suggestions update failed:', error);
        }
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    new Dashboard();
});
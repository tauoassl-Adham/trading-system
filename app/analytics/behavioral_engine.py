import sqlite3
import pandas as pd

class BehavioralEngine:
    def __init__(self, db_name="trading_journal.db"):
        self.db_name = db_name

    def get_performance_report(self):
        """تحليل الصفقات السابقة لاستخراج ملاحظات ذكية"""
        df = pd.read_sql_query("SELECT * FROM trades", sqlite3.connect(self.db_name))
        
        if df.empty: return "لا توجد صفقات كافية للتحليل بعد."
        
        win_rate = (df[df['pnl'] > 0].shape[0] / df.shape[0]) * 100
        avg_pnl = df['pnl'].mean()
        
        report = f"📊 تقرير الأداء:\n- نسبة النجاح: {win_rate:.2f}%\n- متوسط الربح لكل صفقة: ${avg_pnl:.2f}"
        
        # الذكاء الاصطناعي البسيط:
        if win_rate < 50:
            report += "\n💡 ملاحظة: نسبة نجاحك منخفضة. هل فكرت في تقليل عدد الصفقات وزيادة جودة الـ (Core layer)؟"
            
        return report
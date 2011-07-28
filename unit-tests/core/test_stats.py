'''
Created on Jul 25, 2011

@author: sdaubin
'''
from newrelic.core.stats import TimeStats
from newrelic.core.stats import ApdexStats
from newrelic.core.stats import StatsDict
from newrelic.core.apdex import ApdexSetting
import unittest

class ApdexStatsTest(unittest.TestCase):
    
    def test_record_time_in_millis(self):
        apdex = ApdexSetting(50)
        s = ApdexStats(apdex)
        
        s.record_time_in_millis(40)
        s.record_time_in_millis(50)
        s.record_time_in_millis(51)
        
        self.assertEqual(2, s.satisfying)
        self.assertEqual(1, s.tolerating)
        self.assertEqual(0, s.frustrating)
        
        s.record_time_in_millis(200)
        s.record_time_in_millis(201)
        
        self.assertEqual(2, s.tolerating)
        self.assertEqual(1, s.frustrating)

    def test_clone(self):
        apdex = ApdexSetting(50)
        s = ApdexStats(apdex)
        s = s.clone()
        
        s.record_time_in_millis(40)
        s.record_time_in_millis(50)
        s.record_time_in_millis(51)
        
        self.assertEqual(2, s.satisfying)
        self.assertEqual(1, s.tolerating)
        self.assertEqual(0, s.frustrating)
        
        s2 = s.clone()
        s2.record_time_in_millis(75)
        
        self.assertEqual(2, s2.tolerating)
        self.assertEqual(1, s.tolerating)
        
    def test_merge(self):
        apdex = ApdexSetting(50)
        s1 = ApdexStats(apdex)
        
        s1.record_time_in_millis(40)
        s2 = s1.clone();
        
        s1.record_time_in_millis(50)
        s1.record_time_in_millis(51)
        
        s2.record_time_in_millis(251)
        s2.record_time_in_millis(88)
        s2.record_time_in_millis(12)
        
        s1.merge(s2)
        
        self.assertEqual(4, s1.satisfying)
        self.assertEqual(2, s1.tolerating)
        self.assertEqual(1, s1.frustrating)

class TimeStatsTest(unittest.TestCase):


    def test_record(self):
        s = TimeStats()
        self.assertEqual(0,s.call_count)
        self.assertEqual(0,s.min_call_time)
        self.assertEqual(0,s.max_call_time)
        
        s.record(102,50)
        self.assertEqual(102,s.min_call_time)
        self.assertEqual(102,s.max_call_time)
        s.record(23,20)
        s.record(33,33)
        
        self.assertEqual(3,s.call_count)
        self.assertEqual(158,s.total_call_time)
        self.assertEqual(103,s.total_exclusive_call_time)
        self.assertEqual(23,s.min_call_time)
        self.assertEqual(102,s.max_call_time)

    def test_clone(self):
        s1 = TimeStats()
        s2 = s1.clone()
                
        self.assertEqual(0,s2.call_count)
        self.assertEqual(0,s2.total_call_time)
        
        s1.record(5,5)
        
        self.assertEqual(0,s2.call_count)
        self.assertEqual(0,s2.total_call_time)
        
        s2 = s1.clone()
        
        self.assertEqual(1,s2.call_count)
        self.assertEqual(5,s2.total_call_time)
        
        self.assertEqual(5,s2.total_exclusive_call_time)
        self.assertEqual(5,s2.min_call_time)
        self.assertEqual(5,s2.max_call_time)
        
    def test_merge(self):
        s1 = TimeStats()
        s1.record(5,5)
        s2 = s1.clone()
        s2.record(34,10)
                
        self.assertEqual(2,s2.call_count)
        self.assertEqual(39,s2.total_call_time)
        
        s1.merge(s2)
        
        self.assertEqual(3,s1.call_count)
        self.assertEqual(44,s1.total_call_time)
        
        self.assertEqual(20,s1.total_exclusive_call_time)
        self.assertEqual(5,s1.min_call_time)
        self.assertEqual(34,s1.max_call_time)  
        
class StatsDictTest(unittest.TestCase):


    def test_get_apdex_stats(self):        
        d = StatsDict(ApdexSetting(1000))
        s = d.get_apdex_stats("test")
        
        s.record_time_in_millis(555)
        s.record_time_in_millis(1023)
        
        s2 = d.get_apdex_stats("test")
        self.assertEqual(s,s2)
        
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
# -*- coding: utf-8 -*-
"""
电力消费管理API系统
Created on Sat Jan 18 10:32:54 2025

本模块实现了电力消费管理系统的核心API功能，包括：
1. 账户注册和管理
2. 电表读数接收
3. 用电量查询
4. 账单查询

@author: Lenovo
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class ElectricityAccount:
    """电力账户类，用于存储和管理单个用户的电力使用数据"""
    
    def __init__(self, account_id: str, owner_name: str, address: str):
        self.account_id = account_id
        self.owner_name = owner_name
        self.address = address
        self.family_members = []  # 存储家庭成员信息
        self.consumption_data = {}  # 存储用电量数据，格式：{timestamp: consumption}
        self.created_at = datetime.now()

class ElectricityManagementSystem:
    """电力管理系统主类，实现核心API功能"""
    
    def __init__(self):
        self.accounts: Dict[str, ElectricityAccount] = {}  # 存储所有账户
        
    def register_account(self, owner_name: str, address: str) -> str:
        """
        注册新账户
        
        Args:
            owner_name: 户主姓名
            address: 住址
            
        Returns:
            str: 新创建的账户ID
        """
        account_id = f"ACC_{len(self.accounts) + 1}"
        self.accounts[account_id] = ElectricityAccount(account_id, owner_name, address)
        return account_id
    
    def record_consumption(self, account_id: str, timestamp: datetime, consumption: float) -> bool:
        """
        记录半小时用电量数据
        
        Args:
            account_id: 账户ID
            timestamp: 时间戳
            consumption: 用电量(kWh)
            
        Returns:
            bool: 是否成功记录数据
        """
        if account_id not in self.accounts:
            return False
        
        self.accounts[account_id].consumption_data[timestamp] = consumption
        return True
    
    def get_consumption(self, account_id: str, period: str) -> Optional[float]:
        """
        查询指定期间的用电量
        
        Args:
            account_id: 账户ID
            period: 查询期间 ('last_30min', 'today', 'this_week', 'this_month', 'last_month')
            
        Returns:
            float: 总用电量
        """
        if account_id not in self.accounts:
            return None
            
        account = self.accounts[account_id]
        now = datetime.now()
        
        if period == 'last_30min':
            start_time = now - timedelta(minutes=30)
        elif period == 'today':
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'this_week':
            start_time = now - timedelta(days=now.weekday())
            start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'this_month':
            start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == 'last_month':
            first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start_time = first_day_this_month - timedelta(days=1)
            start_time = start_time.replace(day=1)
            end_time = first_day_this_month
            return sum(consumption for timestamp, consumption in account.consumption_data.items()
                      if start_time <= timestamp < end_time)
        
        return sum(consumption for timestamp, consumption in account.consumption_data.items()
                  if timestamp >= start_time)
    
    def get_last_month_bill(self, account_id: str) -> Optional[float]:
        """
        获取上月账单（仅kWh）
        
        Args:
            account_id: 账户ID
            
        Returns:
            float: 上月总用电量
        """
        return self.get_consumption(account_id, 'last_month')

# 创建系统实例
ems = ElectricityManagementSystem()


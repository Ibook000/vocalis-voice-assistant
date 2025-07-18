import asyncio
import os
import json
from typing import Optional
from contextlib import AsyncExitStack

from openai import OpenAI  


from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client



class MCPClient:
    def __init__(self):
        """初始化 MCP 客户端，加载配置文件和MCP服务器列表"""
        self.exit_stack = AsyncExitStack()
        
        # 读取主配置文件
        # 使用UTF-8编码打开配置文件，避免中文解码错误
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 读取MCP服务器配置
        try:
            # 使用UTF-8编码打开MCP配置文件，避免中文解码错误
            with open('mcp.json', 'r', encoding='utf-8') as f:
                mcp_config = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError("❌ mcp.json文件不存在，请确保该文件在项目根目录")
        except json.JSONDecodeError:
            raise ValueError("❌ mcp.json格式错误，请检查JSON语法")
        
        self.openai_api_key = config.get('openai_api_key')
        self.base_url = config.get('base_url')
        self.model = config.get('model')  # 默认模型
        self.system_prompt = config.get('system_prompt', '')  # 系统提示词
        self.mcp_servers = mcp_config.get('mcpServers', {})  # 加载所有MCP服务器配置
        
        if not self.openai_api_key:
            raise ValueError("❌ 未找到 OpenAI API Key，请在 config.json 文件中设置 openai_api_key")
        if not self.mcp_servers:
            raise ValueError("❌ 未找到MCP服务器配置，请检查mcp.json文件")
        
        self.client = OpenAI(api_key=self.openai_api_key, base_url=self.base_url) # 创建OpenAI client
        self.session: Optional[ClientSession] = None
        self.servers = {}
        # 初始化对话历史列表，包含系统提示词
        self.messages = [{"role": "system", "content": self.system_prompt}]
        self.exit_stack = AsyncExitStack()        

    async def connect_to_server(self, server_name: str):
        """根据服务器名称连接到指定的MCP服务器并列出可用工具"""
        # 获取服务器配置
        server_config = self.mcp_servers.get(server_name)
        if not server_config:
            raise ValueError(f"❌ 未找到名为 '{server_name}' 的MCP服务器配置，请检查mcp.json\n可用服务器: {list(self.mcp_servers.keys())}")

        # 构建服务器参数
        server_params = StdioServerParameters(
            command=server_config['command'],
            args=server_config['args'],
            env=None
        )

        # 启动 MCP 服务器并建立通信
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        # 创建并存储会话
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
        self.servers[server_name] = session
        
        # 初始化并获取工具列表
        await session.initialize()
        response = await session.list_tools()
        tools = response.tools
        print(f"\n{server_name} 服务器支持工具:", [tool.name for tool in tools])


        
    async def process_query(self, query: str) -> str:
        """
        使用大模型处理查询并调用可用的 MCP 工具 (Function Calling)
        """
        # 系统提示词 - 定义AI助手的角色和行为准则
        # 添加用户当前查询到对话历史
        self.messages.append({"role": "user", "content": query})
        
        # 列出所有已连接服务器的工具
        all_tools = []
        for server_name, session in self.servers.items():
            try:
                response = await session.list_tools()
                server_tools = [{
                    **tool.model_dump(),
                    "server_name": server_name  # 添加服务器名称标识
                } for tool in response.tools]
                all_tools.extend(server_tools)
                print(f"\n{server_name} 服务器支持工具:", [t['name'] for t in server_tools])
            except Exception as e:
                print(f"⚠️ 获取 {server_name} 工具列表失败: {str(e)}")
        
        if not all_tools:
            raise ValueError("❌ 未从任何MCP服务器获取到工具")
        
        available_tools = [{
              "type": "function",
              "function": {
                  "name": f"{tool['server_name']}_{tool['name']}",  # 添加服务器前缀
                  "description": f"[{tool['server_name']}] {tool['description']}",  # 注明服务器来源
                  "input_schema": tool['inputSchema']
              }
          } for tool in all_tools]
        # print(available_tools)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=available_tools     
        )
        
        # 处理返回的内容
        content = response.choices[0]
        if content.finish_reason == "tool_calls":
            # 将工具调用信息添加到对话历史（包含所有tool_calls）
            self.messages.append(content.message.model_dump())
            
            # 处理每个工具调用
            for tool_call in content.message.tool_calls:
                full_tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # 解析服务器名称和工具名称
                if '_' in full_tool_name:
                    server_name, tool_name = full_tool_name.split('_', 1)
                    session = self.servers.get(server_name)
                    if not session:
                        raise ValueError(f"❌ 未找到服务器 '{server_name}' 的连接会话")
                else:
                    raise ValueError(f"❌ 工具名称格式错误，应为 'server_name_tool_name': {full_tool_name}")
                
                # 执行工具
                result = await session.call_tool(tool_name, tool_args)
                print(f"\n\n[Calling tool {tool_name} with args {tool_args}]\n\n")
                print(result.content[0].text)
                # 添加工具响应消息
                self.messages.append({
                    "role": "tool",
                    "content": result.content[0].text,
                    "tool_call_id": tool_call.id,
                })
            
            # 将上面的结果再返回给大模型用于生产最终的结果
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
            )
            # 将助手回复添加到对话历史
            self.messages.append({"role": "assistant", "content": response.choices[0].message.content})
            return response.choices[0].message.content
            
        # 将助手直接回复添加到对话历史
        self.messages.append({"role": "assistant", "content": content.message.content})
        return content.message.content
    
    async def chat_loop(self):
        """运行交互式聊天循环"""
        print("\n🤖 MCP 客户端已启动！输入 'quit' 退出")

        while True:
            try:
                query = input("\n😀: ").strip()
                if query.lower() == 'quit':
                    break
                response = await self.process_query(query)
                print(f"\n🤖: {response}")

            except Exception as e:
                print(f"\n⚠️ 发生错误: {str(e)}")

    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()

async def main():
    client = MCPClient()
    try:
        # 连接所有MCP服务器
        print("正在连接所有MCP服务器...")
        for server_name in client.mcp_servers.keys():
            try:
                await client.connect_to_server(server_name)
                print(f"✅ 成功连接到 {server_name}")
            except Exception as e:
                print(f"⚠️ 连接 {server_name} 失败: {str(e)}")

        if not client.servers:
            print("❌ 没有成功连接到任何MCP服务器，程序退出")
            return

        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())
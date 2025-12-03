import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from rich.console import Console
from rich.prompt import Prompt # Import Prompt for mocking
from mcp_client_for_ollama.utils.hil_manager import HumanInTheLoopManager
from mcp import Tool

@pytest.fixture
def mock_console():
    """Fixture for a mocked Rich Console."""
    mock = MagicMock(spec=Console)
    # Mock the print method to capture calls
    mock.print = MagicMock()
    return mock

@pytest.fixture
def mock_tool_manager():
    """Fixture for a mocked ToolManager."""
    mock = MagicMock()
    mock.get_available_tools.return_value = [
        Tool(name="builtin.set_system_prompt", description="desc", inputSchema={}),
        Tool(name="builtin.get_system_prompt", description="desc", inputSchema={}),
        Tool(name="builtin.execute_python_code", description="desc", inputSchema={}),
        Tool(name="filesystem.read_file", description="desc", inputSchema={}),
        Tool(name="filesystem.write_file", description="desc", inputSchema={}),
        Tool(name="web.fetch", description="desc", inputSchema={}),
    ]
    return mock

@pytest.fixture
def hil_manager(mock_console, mock_tool_manager):
    """Fixture for HumanInTheLoopManager."""
    manager = HumanInTheLoopManager(mock_console, mock_tool_manager)
    manager._initialize_server_configs() # Ensure initial config is populated
    return manager



# --- Test _get_default_hil_config ---
def test_get_default_hil_config(hil_manager):
    config = hil_manager._get_default_hil_config()
    assert config["global_enabled"] is True
    assert isinstance(config["servers"], dict)
    assert len(config["servers"]) == 0 # Should be empty before initialization

# --- Test _initialize_server_configs ---
def test_initialize_server_configs(hil_manager, mock_tool_manager):
    hil_manager._hil_config = hil_manager._get_default_hil_config() # Reset to default
    hil_manager._initialize_server_configs()
    
    assert "builtin" in hil_manager._hil_config["servers"]
    assert hil_manager._hil_config["servers"]["builtin"]["enabled"] is True
    assert "builtin.set_system_prompt" in hil_manager._hil_config["servers"]["builtin"]["tools"]
    assert hil_manager._hil_config["servers"]["builtin"]["tools"]["builtin.set_system_prompt"] is True

    assert "filesystem" in hil_manager._hil_config["servers"]
    assert hil_manager._hil_config["servers"]["filesystem"]["enabled"] is True
    assert "filesystem.read_file" in hil_manager._hil_config["servers"]["filesystem"]["tools"]
    assert hil_manager._hil_config["servers"]["filesystem"]["tools"]["filesystem.read_file"] is True

    assert "web" in hil_manager._hil_config["servers"]
    assert hil_manager._hil_config["servers"]["web"]["enabled"] is True
    assert "web.fetch" in hil_manager._hil_config["servers"]["web"]["tools"]
    assert hil_manager._hil_config["servers"]["web"]["tools"]["web.fetch"] is True

# --- Test is_enabled ---
def test_is_enabled_global_disabled(hil_manager):
    hil_manager._hil_config["global_enabled"] = False
    assert hil_manager.is_enabled("builtin.set_system_prompt") is False

def test_is_enabled_server_disabled(hil_manager):
    hil_manager._hil_config["servers"]["builtin"]["enabled"] = False
    assert hil_manager.is_enabled("builtin.set_system_prompt") is False
    assert hil_manager.is_enabled("filesystem.read_file") is True # Other server still enabled

def test_is_enabled_tool_disabled(hil_manager):
    hil_manager._hil_config["servers"]["builtin"]["tools"]["builtin.set_system_prompt"] = False
    assert hil_manager.is_enabled("builtin.set_system_prompt") is False
    assert hil_manager.is_enabled("builtin.get_system_prompt") is True # Other tool in same server still enabled

def test_is_enabled_all_enabled(hil_manager):
    assert hil_manager.is_enabled("builtin.set_system_prompt") is True
    assert hil_manager.is_enabled("filesystem.read_file") is True

def test_is_enabled_unknown_tool_or_server(hil_manager):
    assert hil_manager.is_enabled("unknown_server.unknown_tool") is False # Default to False for unknown

# --- Test toggle_global ---
def test_toggle_global(hil_manager, mock_console):
    hil_manager._hil_config["global_enabled"] = True
    hil_manager.toggle_global()
    assert hil_manager._hil_config["global_enabled"] is False
    mock_console.print.assert_any_call("[green]Global HIL confirmations disabled![/green]")

    hil_manager.toggle_global()
    assert hil_manager._hil_config["global_enabled"] is True
    mock_console.print.assert_any_call("[green]Global HIL confirmations enabled![/green]")

# --- Test _set_global_enabled ---
def test_set_global_enabled(hil_manager):
    hil_manager._set_global_enabled(False)
    assert hil_manager._hil_config["global_enabled"] is False
    hil_manager._set_global_enabled(True)
    assert hil_manager._hil_config["global_enabled"] is True

# --- Test _set_server_enabled ---
def test_set_server_enabled(hil_manager, mock_console):
    hil_manager._set_server_enabled("builtin", False)
    assert hil_manager._hil_config["servers"]["builtin"]["enabled"] is False
    assert hil_manager._hil_config["servers"]["builtin"]["tools"]["builtin.set_system_prompt"] is False
    mock_console.print.assert_any_call("[green]HIL for server 'builtin' disabled![/green]")

    hil_manager._set_server_enabled("builtin", True)
    assert hil_manager._hil_config["servers"]["builtin"]["enabled"] is True
    assert hil_manager._hil_config["servers"]["builtin"]["tools"]["builtin.set_system_prompt"] is True
    mock_console.print.assert_any_call("[green]HIL for server 'builtin' enabled![/green]")

def test_set_server_enabled_unknown_server(hil_manager, mock_console):
    hil_manager._set_server_enabled("unknown_server", False)
    mock_console.print.assert_any_call("[red]Server 'unknown_server' not found in HIL configuration.[/red]")

# --- Test _set_tool_enabled ---
def test_set_tool_enabled(hil_manager, mock_console):
    hil_manager._set_tool_enabled("builtin.set_system_prompt", False)
    assert hil_manager._hil_config["servers"]["builtin"]["tools"]["builtin.set_system_prompt"] is False
    mock_console.print.assert_any_call("[green]HIL for tool 'builtin.set_system_prompt' disabled![/green]")

    hil_manager._set_tool_enabled("builtin.set_system_prompt", True)
    assert hil_manager._hil_config["servers"]["builtin"]["tools"]["builtin.set_system_prompt"] is True
    mock_console.print.assert_any_call("[green]HIL for tool 'builtin.set_system_prompt' enabled![/green]")

def test_set_tool_enabled_unknown_tool(hil_manager, mock_console):
    hil_manager._set_tool_enabled("builtin.unknown_tool", False)
    mock_console.print.assert_any_call("[red]Tool 'builtin.unknown_tool' not found in server 'builtin'.[/red]")

def test_set_tool_enabled_unknown_server_for_tool(hil_manager, mock_console):
    hil_manager._set_tool_enabled("unknown_server.some_tool", False)
    mock_console.print.assert_any_call("[red]Server 'unknown_server' not found for tool 'unknown_server.some_tool'.[/red]")

# --- Test request_tool_confirmation ---
@pytest.mark.asyncio
async def test_request_tool_confirmation_hil_disabled_for_tool(hil_manager, mocker):
    hil_manager._hil_config["servers"]["builtin"]["tools"]["builtin.set_system_prompt"] = False
    # No prompt should be displayed, so no need to mock Prompt.ask
    result = await hil_manager.request_tool_confirmation("builtin.set_system_prompt", {"prompt": "new"})
    assert result is True
    hil_manager.console.print.assert_not_called() # No prompt should be displayed

@pytest.mark.asyncio
async def test_request_tool_confirmation_hil_enabled_user_yes(hil_manager, mock_console, mocker):
    mocker.patch('rich.prompt.Prompt.ask', return_value="y")
    result = await hil_manager.request_tool_confirmation("builtin.set_system_prompt", {"prompt": "new"})
    assert result is True
    mock_console.print.assert_any_call("[bold yellow]🧑‍💻 Human-in-the-Loop Confirmation[/bold yellow]")
    mock_console.print.assert_any_call("[cyan]Tool to execute:[/cyan] [bold]builtin.set_system_prompt[/bold]")

@pytest.mark.asyncio
async def test_request_tool_confirmation_hil_enabled_user_no(hil_manager, mock_console, mocker):
    mocker.patch('rich.prompt.Prompt.ask', return_value="n")
    result = await hil_manager.request_tool_confirmation("builtin.set_system_prompt", {"prompt": "new"})
    assert result is False
    mock_console.print.assert_any_call("[yellow]⏭️  Tool call skipped[/yellow]")

@pytest.mark.asyncio
async def test_request_tool_confirmation_user_disable_tool(hil_manager, mock_console, mocker):
    mocker.patch('rich.prompt.Prompt.ask', return_value="disable-tool")
    result = await hil_manager.request_tool_confirmation("builtin.set_system_prompt", {"prompt": "new"})
    assert result is True
    assert hil_manager._hil_config["servers"]["builtin"]["tools"]["builtin.set_system_prompt"] is False
    mock_console.print.assert_any_call("[green]HIL for tool 'builtin.set_system_prompt' disabled![/green]")

@pytest.mark.asyncio
async def test_request_tool_confirmation_user_disable_server(hil_manager, mock_console, mocker):
    mocker.patch('rich.prompt.Prompt.ask', return_value="disable-server")
    result = await hil_manager.request_tool_confirmation("builtin.set_system_prompt", {"prompt": "new"})
    assert result is True
    assert hil_manager._hil_config["servers"]["builtin"]["enabled"] is False
    assert hil_manager._hil_config["servers"]["builtin"]["tools"]["builtin.set_system_prompt"] is False
    mock_console.print.assert_any_call("[green]HIL for server 'builtin' disabled![/green]")

@pytest.mark.asyncio
async def test_request_tool_confirmation_user_disable_all(hil_manager, mock_console, mocker):
    mocker.patch('rich.prompt.Prompt.ask', return_value="disable-all")
    result = await hil_manager.request_tool_confirmation("builtin.set_system_prompt", {"prompt": "new"})
    assert result is True
    assert hil_manager._hil_config["global_enabled"] is False
    mock_console.print.assert_any_call("[dim]Global HIL disabled. All tools will now execute automatically.[/dim]")

@pytest.mark.asyncio
async def test_request_tool_confirmation_user_config(hil_manager, mock_console, mocker):
    mocker.patch('rich.prompt.Prompt.ask', return_value="config")
    # Mock the interactive call, it's not async
    hil_manager.configure_hil_interactive = MagicMock() 
    result = await hil_manager.request_tool_confirmation("builtin.set_system_prompt", {"prompt": "new"})
    assert result is False
    hil_manager.configure_hil_interactive.assert_called_once_with(None)

# --- Test configure_hil_interactive ---
def test_configure_hil_interactive_toggle_global(hil_manager, mock_console, mocker):
    # Mock _display_hil_menu to prevent console output during interactive loop
    mocker.patch.object(hil_manager, '_display_hil_menu')
    
    # Initial state
    hil_manager._hil_config["global_enabled"] = True
    
    # Simulate user input: '1' to toggle global, then 's' to save
    mocker.patch('rich.prompt.Prompt.ask', side_effect=["1", "s"])
    
    hil_manager.configure_hil_interactive(None)
    
    # Assert the final state of the config
    assert hil_manager._hil_config["global_enabled"] is False
    
    # Assert that a message indicating save was printed
    mock_console.print.assert_any_call("[green]HIL configuration saved.[/green]")

def test_configure_hil_interactive_toggle_server(hil_manager, mock_console, mocker):
    # Mock _display_hil_menu to prevent console output during interactive loop
    mocker.patch.object(hil_manager, '_display_hil_menu')

    # Initial state
    hil_manager._hil_config["servers"]["filesystem"]["enabled"] = True
    
    # Simulate user input: 's3' to toggle filesystem server, then 's' to save
    mocker.patch('rich.prompt.Prompt.ask', side_effect=["s3", "s"])
    
    hil_manager.configure_hil_interactive(None)
    
    # Assert the final state of the config
    assert hil_manager._hil_config["servers"]["filesystem"]["enabled"] is False
    
    # Assert that a message indicating save was printed
    mock_console.print.assert_any_call("[green]HIL configuration saved.[/green]")

def test_configure_hil_interactive_toggle_tool(hil_manager, mock_console, mocker):
    # Mock _display_hil_menu to prevent console output during interactive loop
    mocker.patch.object(hil_manager, '_display_hil_menu')

    # Initial state
    hil_manager._hil_config["servers"]["builtin"]["tools"]["builtin.set_system_prompt"] = True
    
    # Simulate user input: 't1' (assuming it maps to builtin.set_system_prompt), then tool name, then 's' to save
    mocker.patch('rich.prompt.Prompt.ask', side_effect=["t1", "builtin.set_system_prompt", "s"])
    
    hil_manager.configure_hil_interactive(None)
    
    # Assert the final state of the config
    assert hil_manager._hil_config["servers"]["builtin"]["tools"]["builtin.set_system_prompt"] is False
    
    # Assert that a message indicating save was printed
    mock_console.print.assert_any_call("[green]HIL configuration saved.[/green]")

def test_configure_hil_interactive_save(hil_manager, mock_console, mocker):
    # Mock _display_hil_menu to prevent console output during interactive loop
    mocker.patch.object(hil_manager, '_display_hil_menu')

    # Initial state
    hil_manager._hil_config["global_enabled"] = True
    
    # Simulate user input: '1' to toggle global, then 's' to save
    mocker.patch('rich.prompt.Prompt.ask', side_effect=["1", "s"])
    
    hil_manager.configure_hil_interactive(None)
    
    # Assert the final state of the config
    assert hil_manager._hil_config["global_enabled"] is False
    
    # Assert that a message indicating save was printed
    mock_console.print.assert_any_call("[green]HIL configuration saved.[/green]")

def test_configure_hil_interactive_quit_reverts(hil_manager, mock_console, mocker):
    # Mock _display_hil_menu to prevent console output during interactive loop
    mocker.patch.object(hil_manager, '_display_hil_menu')

    # Initial state
    original_global_state = hil_manager._hil_config["global_enabled"]
    
    # Simulate user input: '1' to toggle global, then 'q' to quit (revert changes)
    mocker.patch('rich.prompt.Prompt.ask', side_effect=["1", "q"])
    
    hil_manager.configure_hil_interactive(None)
    
    # Assert that the global state reverted to its original value
    assert hil_manager._hil_config["global_enabled"] == original_global_state
    
    # Assert that a message indicating cancellation was printed
    mock_console.print.assert_any_call("[yellow]HIL configuration changes cancelled.[/yellow]")
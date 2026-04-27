package com.microimage.crm.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.microimage.crm.api.RetrofitClient
import com.microimage.crm.model.Proposal
import com.microimage.crm.model.SalesActivity
import com.microimage.crm.model.SalesFunnel
import com.microimage.crm.ui.Screen
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(token: String, navController: NavController) {
    val scope = rememberCoroutineScope()
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    
    var funnelEntries by remember { mutableStateOf<List<SalesFunnel>>(emptyList()) }
    var proposals by remember { mutableStateOf<List<Proposal>>(emptyList()) }
    var activities by remember { mutableStateOf<List<SalesActivity>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var userRole by remember { mutableStateOf("") }

    LaunchedEffect(Unit) {
        scope.launch {
            try {
                val authHeader = "Token $token"
                
                // Get current user role
                val userRes = RetrofitClient.apiService.getCurrentUser(authHeader)
                if (userRes.isSuccessful) {
                    userRole = userRes.body()?.role ?: ""
                }

                val funnelResponse = RetrofitClient.apiService.getSalesFunnel(authHeader)
                val proposalsResponse = RetrofitClient.apiService.getProposals(authHeader)
                val activitiesResponse = RetrofitClient.apiService.getSalesActivities(authHeader)

                if (funnelResponse.isSuccessful) funnelEntries = funnelResponse.body() ?: emptyList()
                if (proposalsResponse.isSuccessful) proposals = proposalsResponse.body() ?: emptyList()
                if (activitiesResponse.isSuccessful) activities = activitiesResponse.body() ?: emptyList()

            } catch (e: Exception) {
                errorMessage = "Failed to load data: ${e.message}"
            } finally {
                isLoading = false
            }
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet {
                Spacer(modifier = Modifier.height(16.dp))
                Text("MiCRM Menu", modifier = Modifier.padding(16.dp), style = MaterialTheme.typography.titleLarge)
                
                NavigationDrawerItem(
                    label = { Text("Dashboard") },
                    selected = true,
                    onClick = { scope.launch { drawerState.close() } }
                )

                Divider(modifier = Modifier.padding(vertical = 8.dp))
                Text("Customers", modifier = Modifier.padding(16.dp), style = MaterialTheme.typography.labelMedium)
                
                NavigationDrawerItem(
                    label = { Text("Customer List") },
                    selected = false,
                    onClick = { 
                        scope.launch { drawerState.close() }
                        navController.navigate(Screen.CustomerList.createRoute(token)) 
                    }
                )
                NavigationDrawerItem(
                    label = { Text("My Requests") },
                    selected = false,
                    onClick = { 
                        scope.launch { drawerState.close() }
                        navController.navigate(Screen.MyCustomerRequests.createRoute(token)) 
                    }
                )
                if (userRole == "manager" || userRole == "admin") {
                    NavigationDrawerItem(
                        label = { Text("Pending Customer Requests") },
                        selected = false,
                        onClick = { 
                            scope.launch { drawerState.close() }
                            navController.navigate(Screen.PendingCustomerRequests.createRoute(token)) 
                        }
                    )
                }

                Divider(modifier = Modifier.padding(vertical = 8.dp))
                Text("Sales", modifier = Modifier.padding(16.dp), style = MaterialTheme.typography.labelMedium)

                NavigationDrawerItem(
                    label = { Text("Sales Funnel") },
                    selected = false,
                    onClick = { 
                        scope.launch { drawerState.close() }
                        navController.navigate(Screen.SalesFunnel.createRoute(token)) 
                    }
                )
                NavigationDrawerItem(
                    label = { Text("Sales Proposals") },
                    selected = false,
                    onClick = { 
                        scope.launch { drawerState.close() }
                        navController.navigate(Screen.SalesProposal.createRoute(token)) 
                    }
                )
                if (userRole == "manager" || userRole == "admin") {
                    NavigationDrawerItem(
                        label = { Text("Pending Proposal Approvals") },
                        selected = false,
                        onClick = { 
                            scope.launch { drawerState.close() }
                            navController.navigate(Screen.PendingProposalApprovals.createRoute(token)) 
                        }
                    )
                }

                Divider(modifier = Modifier.padding(vertical = 8.dp))
                Text("Marketing", modifier = Modifier.padding(16.dp), style = MaterialTheme.typography.labelMedium)
                NavigationDrawerItem(
                    label = { Text("Email Campaigns") },
                    selected = false,
                    onClick = { 
                        scope.launch { drawerState.close() }
                        navController.navigate(Screen.CampaignList.createRoute(token)) 
                    }
                )

                Divider(modifier = Modifier.padding(vertical = 8.dp))
                NavigationDrawerItem(
                    label = { Text("Settings & Logout") },
                    selected = false,
                    onClick = { 
                        scope.launch { drawerState.close() }
                        navController.navigate(Screen.Settings.createRoute(token)) 
                    }
                )
            }
        }
    ) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text("Dashboard") },
                    navigationIcon = {
                        IconButton(onClick = { scope.launch { drawerState.open() } }) {
                            Icon(Icons.Default.Menu, contentDescription = "Menu")
                        }
                    },
                    actions = {
                        IconButton(onClick = { navController.navigate(Screen.Settings.createRoute(token)) }) {
                            Icon(Icons.Default.Settings, contentDescription = "Settings")
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = MaterialTheme.colorScheme.primary,
                        titleContentColor = MaterialTheme.colorScheme.onPrimary,
                        navigationIconContentColor = MaterialTheme.colorScheme.onPrimary,
                        actionIconContentColor = MaterialTheme.colorScheme.onPrimary
                    )
                )
            },
            floatingActionButton = {
                FloatingActionButton(onClick = {
                    navController.navigate(Screen.SalesActivityCreate.createRoute(token))
                }) {
                    Icon(Icons.Default.Add, contentDescription = "Log Activity")
                }
            }
        ) { paddingValues ->
            Box(modifier = Modifier.padding(paddingValues).fillMaxSize()) {
                if (isLoading) {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                } else if (errorMessage != null) {
                    Text(
                        text = errorMessage!!,
                        color = MaterialTheme.colorScheme.error,
                        modifier = Modifier.align(Alignment.Center).padding(16.dp)
                    )
                } else {
                    LazyColumn(
                        contentPadding = PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        item {
                            SectionHeader(
                                title = "Sales Funnel", 
                                subtitle = "(${funnelEntries.size} Active)",
                                onSeeAllClick = { navController.navigate(Screen.SalesFunnel.createRoute(token)) }
                            )
                        }
                        if (funnelEntries.isEmpty()) {
                            item { EmptyState("No active deals in funnel") }
                        } else {
                            items(funnelEntries.take(3)) { item ->
                                FunnelCard(item)
                            }
                        }

                        item {
                            SectionHeader(
                                title = "Recent Proposals", 
                                subtitle = "(${proposals.size})",
                                onSeeAllClick = { navController.navigate(Screen.SalesProposal.createRoute(token)) }
                            )
                        }
                        if (proposals.isEmpty()) {
                            item { EmptyState("No proposals found") }
                        } else {
                            items(proposals.take(3)) { proposalItem ->
                                ProposalCard(proposalItem) {
                                    navController.navigate(Screen.ProposalDetail.createRoute(token, proposalItem.id))
                                }
                            }
                        }

                        item {
                            SectionHeader("Upcoming Activities", "(${activities.size})")
                        }
                        if (activities.isEmpty()) {
                            item { EmptyState("No upcoming activities") }
                        } else {
                            items(activities.take(3)) { item ->
                                ActivityCard(item)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun SectionHeader(title: String, subtitle: String = "", onSeeAllClick: (() -> Unit)? = null) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
            if (subtitle.isNotEmpty()) {
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.Gray
                )
            }
        }
        if (onSeeAllClick != null) {
            TextButton(onClick = onSeeAllClick) {
                Text("See All")
            }
        }
    }
}

@Composable
fun EmptyState(message: String) {
    Text(
        text = message,
        style = MaterialTheme.typography.bodyMedium,
        color = Color.Gray,
        modifier = Modifier.padding(start = 8.dp, bottom = 8.dp)
    )
}

@Composable
fun FunnelCard(item: SalesFunnel) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF3E0))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = item.companyName, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(4.dp))
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(text = item.stage, style = MaterialTheme.typography.bodyMedium)
                Text(
                    text = "₱${String.format("%,.2f", item.retail)}",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Bold
                )
            }
            Spacer(modifier = Modifier.height(4.dp))
            LinearProgressIndicator(
                progress = item.probability / 100f,
                modifier = Modifier.fillMaxWidth().height(6.dp),
                color = MaterialTheme.colorScheme.primary
            )
            Text(
                text = "${item.probability}% Probability",
                style = MaterialTheme.typography.labelSmall,
                modifier = Modifier.align(Alignment.End)
            )
        }
    }
}

@Composable
fun ProposalCard(item: Proposal, onClick: () -> Unit = {}) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable { onClick() },
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFE3F2FD))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(text = item.proposalNumber, style = MaterialTheme.typography.labelMedium, color = Color.Gray)
                Text(
                    text = item.status,
                    style = MaterialTheme.typography.labelMedium,
                    color = if (item.status == "Accepted") Color(0xFF2E7D32) else Color.Red,
                    fontWeight = FontWeight.Bold
                )
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = item.subject, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(text = item.customerName, style = MaterialTheme.typography.bodyMedium)
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "${item.currency} ${String.format("%,.2f", item.totalAmount)}",
                style = MaterialTheme.typography.bodyLarge,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}

@Composable
fun ActivityCard(item: SalesActivity) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFF3E5F5))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(12.dp)
                        .background(Color.Magenta, shape = RoundedCornerShape(50))
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(text = item.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            }
            Spacer(modifier = Modifier.height(4.dp))
            Text(text = "Customer: ${item.customerName ?: "N/A"}", style = MaterialTheme.typography.bodyMedium)
            Spacer(modifier = Modifier.height(4.dp))
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(text = item.status, style = MaterialTheme.typography.labelMedium)
                Text(
                    text = item.scheduledStart?.take(10) ?: "No Date",
                    style = MaterialTheme.typography.labelMedium,
                    color = Color.Gray
                )
            }
        }
    }
}
